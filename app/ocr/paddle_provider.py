from __future__ import annotations

from hashlib import sha256
import importlib.util
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Mapping

from app.core.standard_ocr import StandardOCRResult
from app.ocr.adapters.paddle_standard_adapter import PaddleStandardOCRAdapter
from app.ocr.base import OCRInput, OCRProvider
from app.security.sensitive_filter import detect_sensitive_text, redact_sensitive_text
from app.storage.file_store import StoredFileMetadata


class PaddleOCRUnavailable(RuntimeError):
    def __init__(self, diagnostic_code: str = "paddle_not_installed") -> None:
        super().__init__(diagnostic_code)
        self.diagnostic_code = diagnostic_code


class PaddleOCRProvider(OCRProvider):
    """Optional PaddleOCR provider that returns StandardOCRResult.

    The actual paddleocr package is imported lazily inside the execution path.
    Default pytest must be able to import and instantiate this provider without
    installing PaddleOCR.
    """

    provider_name = "paddleocr"
    provider_alias = "paddle"
    ocr_extensions = {".jpg", ".jpeg", ".png"}
    pdf_extensions = {".pdf"}
    skipped_extensions = {".xlsx", ".csv"}

    def __init__(
        self,
        *,
        lang: str = "korean",
        use_angle_cls: bool = True,
        use_gpu: bool = False,
        adapter: PaddleStandardOCRAdapter | None = None,
        ocr_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.use_gpu = use_gpu
        self.adapter = adapter or PaddleStandardOCRAdapter()
        self._ocr_factory = ocr_factory

    def extract(
        self,
        source: OCRInput,
        *,
        source_file_id: str | None = None,
        source_file_name: str | None = None,
    ) -> StandardOCRResult:
        source_info = self._source_info(source, source_file_id, source_file_name)
        suffix = str(source_info["file_extension"])

        if suffix in self.skipped_extensions:
            return self._diagnostic_result(source_info, "skipped", "paddle_not_ocr_target")
        if suffix in self.pdf_extensions:
            return self._diagnostic_result(source_info, "failed", "paddle_pdf_not_supported")
        if suffix not in self.ocr_extensions:
            return self._diagnostic_result(source_info, "failed", "unsupported_input_type")

        try:
            ocr = self._build_ocr(use_textline_orientation=self.use_angle_cls)
        except PaddleOCRUnavailable as exc:
            return self._diagnostic_result(source_info, "failed", exc.diagnostic_code)
        except Exception as exc:
            return self._diagnostic_result(
                source_info,
                "failed",
                "paddle_runtime_error",
                diagnostic_detail_code=_safe_exception_code(exc),
            )

        path = source_info.get("file_path")
        if not isinstance(path, Path) or not path.exists():
            return self._diagnostic_result(source_info, "failed", "source_not_accessible")

        fallback_warning: str | None = None
        try:
            raw_result = self._run_ocr(ocr, path, use_textline_orientation=self.use_angle_cls)
        except ValueError as exc:
            try:
                raw_result = self._run_ocr_with_normalized_image(
                    ocr,
                    path,
                    use_textline_orientation=self.use_angle_cls,
                )
                fallback_warning = "paddle_image_normalization_fallback"
            except Exception as fallback_exc:
                return self._diagnostic_result(
                    source_info,
                    "failed",
                    "paddle_runtime_error",
                    diagnostic_detail_code=_safe_exception_code(fallback_exc or exc),
                )
        except Exception as exc:
            if self.use_angle_cls and isinstance(exc, NotImplementedError):
                try:
                    ocr = self._build_ocr(use_textline_orientation=False)
                    raw_result = self._run_ocr(ocr, path, use_textline_orientation=False)
                    fallback_warning = "paddle_textline_orientation_fallback"
                except Exception as fallback_exc:
                    return self._diagnostic_result(
                        source_info,
                        "failed",
                        "paddle_runtime_error",
                        diagnostic_detail_code=_safe_exception_code(fallback_exc),
                    )
            else:
                return self._diagnostic_result(
                    source_info,
                    "failed",
                    "paddle_runtime_error",
                    diagnostic_detail_code=_safe_exception_code(exc),
                )

        sanitized_result = self._sanitize_result(raw_result)
        if fallback_warning:
            sanitized_result.setdefault("warnings", [])
            sanitized_result["warnings"].append(fallback_warning)
        return self.adapter.convert(
            sanitized_result,
            source_file_id=str(source_info["source_file_id"]),
            source_file_name=str(source_info["source_file_name"]),
            provider_version=sanitized_result.get("engine_version") or "optional",
        )

    def _build_ocr(self, *, use_textline_orientation: bool) -> Any:
        factory = self._ocr_factory
        if factory is None:
            factory = _load_paddle_ocr_class()
            if importlib.util.find_spec("paddle") is None:
                raise PaddleOCRUnavailable("paddle_runtime_missing")
        try:
            return factory(
                lang=self.lang,
                use_angle_cls=use_textline_orientation,
                use_gpu=self.use_gpu,
                show_log=False,
            )
        except TypeError:
            return factory(**self._modern_factory_kwargs(use_textline_orientation=use_textline_orientation))

    def _run_ocr(self, ocr: Any, path: Path, *, use_textline_orientation: bool) -> Any:
        if hasattr(ocr, "ocr"):
            try:
                return ocr.ocr(str(path), cls=use_textline_orientation)
            except NotImplementedError:
                if hasattr(ocr, "predict"):
                    return ocr.predict(
                        str(path),
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_textline_orientation=use_textline_orientation,
                    )
                raise
            except TypeError:
                try:
                    return ocr.ocr(
                        str(path),
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_textline_orientation=use_textline_orientation,
                    )
                except NotImplementedError:
                    if hasattr(ocr, "predict"):
                        return ocr.predict(
                            str(path),
                            use_doc_orientation_classify=False,
                            use_doc_unwarping=False,
                            use_textline_orientation=use_textline_orientation,
                        )
                    raise
        if hasattr(ocr, "predict"):
            return ocr.predict(
                str(path),
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=use_textline_orientation,
            )
        raise PaddleOCRUnavailable("paddle_runtime_error")

    def _run_ocr_with_normalized_image(
        self,
        ocr: Any,
        path: Path,
        *,
        use_textline_orientation: bool,
    ) -> Any:
        from PIL import Image, ImageOps

        with TemporaryDirectory() as temp_dir:
            normalized_path = Path(temp_dir) / "paddle_normalized_input.png"
            with Image.open(path) as image:
                normalized = ImageOps.exif_transpose(image).convert("RGB")
                normalized.save(normalized_path, format="PNG")
            return self._run_ocr(
                ocr,
                normalized_path,
                use_textline_orientation=use_textline_orientation,
            )

    def _modern_factory_kwargs(self, *, use_textline_orientation: bool) -> dict[str, Any]:
        return {
            "lang": self.lang,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": use_textline_orientation,
            "show_log": False,
        }

    def _sanitize_result(self, raw_result: Any) -> dict[str, Any]:
        if _is_sanitized_mapping(raw_result):
            payload = dict(raw_result)
            payload.setdefault("engine", "paddleocr")
            payload.setdefault("engine_version", "optional")
            payload.setdefault("status", "succeeded")
            payload.setdefault("language_hint", self._language_hint())
            payload.setdefault("input_type", "image")
            payload.setdefault("image_count", 1)
            payload.setdefault("has_angle_classifier", self.use_angle_cls)
            payload.setdefault("has_gpu", self.use_gpu)
            return payload

        lines = _lines_from_paddle_output(raw_result)
        status = "succeeded" if lines else "failed"
        diagnostic_code = None if lines else "paddle_no_text_detected"
        warnings = [] if lines else ["paddle_empty_result"]
        key_value_candidates = _candidate_hints_from_lines(lines)
        if key_value_candidates:
            warnings.append("paddle_candidate_hints_generated")
        return {
            "engine": "paddleocr",
            "engine_version": "optional",
            "status": status,
            "language_hint": self._language_hint(),
            "input_type": "image",
            "image_count": 1,
            "has_angle_classifier": self.use_angle_cls,
            "has_gpu": self.use_gpu,
            "confidence": _average_confidence(lines),
            "pages": [{"page_index": 0, "unit": "pixel"}],
            "lines": lines,
            "key_value_candidates": key_value_candidates,
            "diagnostic_code": diagnostic_code,
            "warnings": warnings,
        }

    def _diagnostic_result(
        self,
        source_info: Mapping[str, object],
        status: str,
        diagnostic_code: str,
        *,
        diagnostic_detail_code: str | None = None,
    ) -> StandardOCRResult:
        warnings = [diagnostic_code]
        if diagnostic_detail_code:
            warnings.append(f"detail:{diagnostic_detail_code}")
        payload = {
            "engine": "paddleocr",
            "engine_version": "optional",
            "status": status,
            "language_hint": self._language_hint(),
            "input_type": "image",
            "image_count": 1,
            "has_angle_classifier": self.use_angle_cls,
            "has_gpu": self.use_gpu,
            "pages": [],
            "lines": [],
            "key_value_candidates": [],
            "diagnostic_code": diagnostic_code,
            "diagnostic_detail_code": diagnostic_detail_code,
            "warnings": warnings,
        }
        return self.adapter.convert(
            payload,
            source_file_id=str(source_info["source_file_id"]),
            source_file_name=str(source_info["source_file_name"]),
            provider_version="optional",
        )

    def _source_info(
        self,
        source: OCRInput,
        source_file_id: str | None,
        source_file_name: str | None,
    ) -> dict[str, object]:
        if isinstance(source, StoredFileMetadata):
            file_name = _display_file_name(source_file_name or source.original_file_name)
            stored_relative_path = source.stored_relative_path
            return {
                "source_file_id": source_file_id or _source_file_id(stored_relative_path),
                "source_file_name": file_name,
                "file_extension": source.file_extension.lower(),
                "file_path": Path(stored_relative_path),
            }

        path = Path(source)
        file_name = _display_file_name(source_file_name or path.name or "paddle_input")
        source_key = file_name if path.is_absolute() else path.as_posix()
        return {
            "source_file_id": source_file_id or _source_file_id(source_key),
            "source_file_name": file_name,
            "file_extension": path.suffix.lower(),
            "file_path": path,
        }

    def _language_hint(self) -> str:
        if self.lang.lower() in {"korean", "ko", "ko-kr"}:
            return "ko"
        return self.lang

def _load_paddle_ocr_class() -> Any:
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise PaddleOCRUnavailable("paddle_not_installed") from exc
    except Exception as exc:
        raise PaddleOCRUnavailable("paddle_import_failed") from exc
    return PaddleOCR


def _is_sanitized_mapping(value: Any) -> bool:
    return isinstance(value, Mapping) and (
        "lines" in value or "key_value_candidates" in value or "pages" in value
    )


def _lines_from_paddle_output(raw_result: Any) -> list[dict[str, Any]]:
    line_items: list[tuple[Any, str, float | None]] = []
    _collect_paddle_line_items(raw_result, line_items)
    lines: list[dict[str, Any]] = []
    for index, (bbox, text, confidence) in enumerate(line_items[:120]):
        safe_text = redact_sensitive_text(text)
        detection = detect_sensitive_text(text)
        lines.append(
            {
                "block_id": f"paddle-p0-l{index}",
                "page_index": 0,
                "line_order": index,
                "text": "[REDACTED]" if detection.detected and safe_text == "[REDACTED]" else safe_text,
                "normalized_text": "[REDACTED]" if detection.detected and safe_text == "[REDACTED]" else safe_text,
                "confidence": confidence,
                "bbox": bbox,
                "block_type": "line",
                "sensitive_category": detection.categories[0] if detection.categories else None,
            }
        )
    return lines


def _collect_paddle_line_items(
    value: Any,
    line_items: list[tuple[Any, str, float | None]],
) -> None:
    if _is_paddle_line_item(value):
        bbox, text_confidence = value[0], value[1]
        text, confidence = _text_confidence(text_confidence)
        if text:
            line_items.append((bbox, text, confidence))
        return
    if isinstance(value, Mapping):
        rec_texts = value.get("rec_texts")
        if isinstance(rec_texts, (list, tuple)):
            rec_scores = value.get("rec_scores")
            dt_polys = value.get("dt_polys")
            for index, text in enumerate(rec_texts):
                if text in {None, ""}:
                    continue
                bbox = _sequence_item(dt_polys, index)
                confidence = _optional_float(_sequence_item(rec_scores, index))
                line_items.append((_safe_bbox(bbox), str(text), confidence))
            return
        text = value.get("text") or value.get("content")
        if text not in {None, ""}:
            line_items.append(
                (
                    _safe_bbox(value.get("bbox") or value.get("box") or value.get("polygon")),
                    str(text),
                    _optional_float(value.get("confidence") or value.get("score")),
                )
            )
            return
        for nested_value in value.values():
            _collect_paddle_line_items(nested_value, line_items)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _collect_paddle_line_items(item, line_items)


def _is_paddle_line_item(value: Any) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return False
    return _looks_like_bbox(value[0]) and _text_confidence(value[1])[0] is not None


def _looks_like_bbox(value: Any) -> bool:
    value = _safe_bbox(value)
    if not isinstance(value, (list, tuple)) or len(value) not in {4, 8}:
        return False
    if all(isinstance(item, (int, float)) for item in value):
        return True
    return all(
        isinstance(item, (list, tuple))
        and len(item) == 2
        and all(isinstance(point, (int, float)) for point in item)
        for item in value
    )


def _text_confidence(value: Any) -> tuple[str | None, float | None]:
    if isinstance(value, str):
        return value, None
    if isinstance(value, (list, tuple)) and value:
        text = value[0] if value[0] not in {None, ""} else None
        confidence = _optional_float(value[1]) if len(value) > 1 else None
        return (str(text) if text is not None else None), confidence
    if isinstance(value, Mapping):
        text = value.get("text") or value.get("content")
        confidence = _optional_float(value.get("confidence") or value.get("score"))
        return (str(text) if text not in {None, ""} else None), confidence
    return None, None


def _average_confidence(lines: list[Mapping[str, Any]]) -> float | None:
    values = [
        _normalized_confidence(line.get("confidence"))
        for line in lines
        if _normalized_confidence(line.get("confidence")) is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


DATE_CANDIDATE_PATTERN = re.compile(
    r"\b(?:\d{4}[-./]\d{1,2}[-./]\d{1,2}|\d{8})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?\b"
)
BUSINESS_NUMBER_CANDIDATE_PATTERN = re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{5}\b")
AMOUNT_CANDIDATE_PATTERN = re.compile(
    r"[\-－−–—]?\s*(?:₩\s*)?(?:(?:[0-9OoIl|BSㅇ]{1,3}(?:(?:\s*[,\.]\s*|\s+)[0-9OoIl|BSㅇ]{3})+)|[0-9OoIl|BSㅇ]+)(?:원)?",
    flags=re.IGNORECASE,
)
PHONE_LIKE_PATTERN = re.compile(r"\b\d{2,4}[-\s]\d{3,4}[-\s]\d{4}\b")
CARD_LIKE_PATTERN = re.compile(r"\b\d{4}[-\s]\d{4}[-\s]\d{4}(?:[-\s]\d{4,7})?\b")

TOTAL_LABELS = ("합계", "총액", "총금액", "결제", "받은", "청구", "승인금액", "total", "amount")
FINAL_LABELS = ("합계", "총액", "총금액", "최종", "결제", "받은", "청구", "total")
PAID_LABELS = ("결제", "받은", "카드", "현금", "승인금액", "paid")
SUPPLY_LABELS = ("공급", "공급가", "공급가액", "supply")
VAT_LABELS = ("부가", "세액", "vat", "tax")
DISCOUNT_LABELS = ("할인", "쿠폰", "차감", "discount")
GROSS_LABELS = ("상품금액", "매출", "공급대가", "gross")
PAYMENT_CARD_LABELS = ("카드", "신용", "체크", "card")
PAYMENT_CASH_LABELS = ("현금", "cash")
def _candidate_hints_from_lines(lines: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_types: set[str] = set()

    for line in lines:
        text = _safe_line_text(line)
        if not text:
            continue
        source_block_id = str(line.get("block_id") or "")
        confidence = _optional_float(line.get("confidence"))

        date_match = DATE_CANDIDATE_PATTERN.search(text)
        if date_match:
            _append_candidate(
                candidates,
                seen_types,
                candidate_type="transaction_date",
                key="transaction_date",
                value=date_match.group(0),
                source_block_id=source_block_id,
                confidence=confidence,
            )

        business_match = BUSINESS_NUMBER_CANDIDATE_PATTERN.search(text)
        if business_match:
            _append_candidate(
                candidates,
                seen_types,
                candidate_type="business_number",
                key="business_number",
                value=business_match.group(0),
                source_block_id=source_block_id,
                confidence=confidence,
            )

        compact = _compact_line(text)
        if any(label in compact for label in PAYMENT_CARD_LABELS):
            _append_candidate(
                candidates,
                seen_types,
                candidate_type="payment_method",
                key="payment_method",
                value="카드",
                source_block_id=source_block_id,
                confidence=confidence,
            )
        elif any(label in compact for label in PAYMENT_CASH_LABELS):
            _append_candidate(
                candidates,
                seen_types,
                candidate_type="payment_method",
                key="payment_method",
                value="현금",
                source_block_id=source_block_id,
                confidence=confidence,
            )

        amount = _last_reasonable_amount(text)
        if amount is None:
            continue
        if _has_any_label(compact, SUPPLY_LABELS):
            _append_amount_candidate(candidates, seen_types, "supply_amount", amount, source_block_id, confidence)
        elif _has_any_label(compact, VAT_LABELS):
            _append_amount_candidate(candidates, seen_types, "vat_amount", amount, source_block_id, confidence)
        elif _has_any_label(compact, DISCOUNT_LABELS):
            _append_amount_candidate(candidates, seen_types, "discount_amount", amount, source_block_id, confidence)
        elif _has_any_label(compact, GROSS_LABELS):
            _append_amount_candidate(candidates, seen_types, "gross_amount", amount, source_block_id, confidence)
        elif _has_any_label(compact, PAID_LABELS):
            _append_amount_candidate(candidates, seen_types, "paid_amount", amount, source_block_id, confidence)
            _append_amount_candidate(candidates, seen_types, "total_amount", amount, source_block_id, confidence)
        elif _has_any_label(compact, FINAL_LABELS):
            _append_amount_candidate(candidates, seen_types, "final_amount", amount, source_block_id, confidence)
            _append_amount_candidate(candidates, seen_types, "total_amount", amount, source_block_id, confidence)

    return candidates


def _append_amount_candidate(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    candidate_type: str,
    amount: int,
    source_block_id: str,
    confidence: float | None,
) -> None:
    _append_candidate(
        candidates,
        seen_types,
        candidate_type=candidate_type,
        key=candidate_type,
        value=str(amount),
        source_block_id=source_block_id,
        confidence=confidence,
    )


def _append_candidate(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    *,
    candidate_type: str,
    key: str,
    value: str,
    source_block_id: str,
    confidence: float | None,
) -> None:
    if candidate_type in seen_types:
        return
    text = str(value or "").strip()
    if not text:
        return
    candidate: dict[str, Any] = {
        "key": key,
        "value": text,
        "normalized_value": text,
        "candidate_type": candidate_type,
        "source_block_ids": [source_block_id] if source_block_id else [],
    }
    if confidence is not None:
        candidate["confidence"] = confidence
    candidates.append(candidate)
    seen_types.add(candidate_type)


def _safe_line_text(line: Mapping[str, Any]) -> str | None:
    if line.get("sensitive_category"):
        return None
    text = str(line.get("normalized_text") or line.get("text") or "").strip()
    if not text or text == "[REDACTED]":
        return None
    return text


def _last_reasonable_amount(text: str) -> int | None:
    amounts = [
        amount
        for token in AMOUNT_CANDIDATE_PATTERN.findall(text or "")
        if (amount := _normalize_amount_candidate(token, source_text=text)) is not None
    ]
    if not amounts:
        return None
    return amounts[-1]


def _normalize_amount_candidate(token: object, *, source_text: str) -> int | None:
    text = str(token or "").strip()
    if not text:
        return None
    translated = text.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1", "B": "8", "S": "5", "ㅇ": "0"}))
    grouped = bool(re.search(r"\d\s*[,\.]\s*\d{3}|\d\s+\d{3}", translated))
    digits = re.sub(r"\D", "", translated)
    if not digits:
        return None
    if len(digits) >= 8 and not grouped:
        return None
    if PHONE_LIKE_PATTERN.search(source_text) or CARD_LIKE_PATTERN.search(source_text):
        return None
    try:
        amount = int(digits)
    except ValueError:
        return None
    if amount <= 9 or amount > 10_000_000:
        return None
    return -amount if translated.lstrip().startswith(("-", "－", "−", "–", "—")) else amount


def _has_any_label(compact: str, labels: tuple[str, ...]) -> bool:
    return any(label.lower().replace(" ", "") in compact for label in labels)


def _compact_line(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "").lower())


def _normalized_confidence(value: Any) -> float | None:
    number = _optional_float(value)
    if number is None:
        return None
    if 0 <= number <= 1:
        return number
    if 1 < number <= 100:
        return number / 100
    return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sequence_item(value: Any, index: int) -> Any:
    if isinstance(value, (list, tuple)) and index < len(value):
        return value[index]
    return None


def _safe_bbox(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [_safe_bbox(item) for item in value]
    return value


def _display_file_name(value: str) -> str:
    return Path(str(value).replace("\\", "/")).name


def _source_file_id(value: str | None) -> str:
    return sha256((value or "unknown").encode("utf-8")).hexdigest()


def _safe_exception_code(exc: Exception) -> str:
    name = exc.__class__.__name__
    normalized = []
    for char in name:
        if char.isupper() and normalized:
            normalized.append("_")
        normalized.append(char.lower())
    return "".join(normalized).replace("__", "_")
