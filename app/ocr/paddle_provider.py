from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from hashlib import sha256
import importlib
import importlib.util
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any, Callable, Mapping

from app.classifier.merchant_dictionary import find_merchant_by_business_number, find_merchant_by_name_fragment
from app.core.standard_ocr import StandardOCRResult
from app.ocr.adapters.paddle_standard_adapter import PaddleStandardOCRAdapter
from app.ocr.base import OCRInput, OCRProvider
from app.security.sensitive_filter import detect_sensitive_text, redact_sensitive_text
from app.storage.file_store import StoredFileMetadata


class PaddleOCRUnavailable(RuntimeError):
    def __init__(self, diagnostic_code: str = "paddle_not_installed") -> None:
        super().__init__(diagnostic_code)
        self.diagnostic_code = diagnostic_code


_GLOBAL_OCR_INSTANCES: dict[tuple[str, bool, bool, bool], Any] = {}


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
        use_angle_cls: bool = False,
        use_gpu: bool = False,
        show_log: bool = False,
        adapter: PaddleStandardOCRAdapter | None = None,
        ocr_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.use_gpu = use_gpu
        self.show_log = show_log
        self.adapter = adapter or PaddleStandardOCRAdapter()
        self._ocr_factory = ocr_factory
        self._ocr_instances: dict[bool, Any] = {}

    def extract(
        self,
        source: OCRInput,
        *,
        source_file_id: str | None = None,
        source_file_name: str | None = None,
    ) -> StandardOCRResult:
        total_started_at = perf_counter()
        init_elapsed_ms = 0
        ocr_elapsed_ms = 0
        device_diagnostics: dict[str, Any] = _unknown_paddle_device_diagnostics()
        source_info = self._source_info(source, source_file_id, source_file_name)
        suffix = str(source_info["file_extension"])

        if suffix in self.skipped_extensions:
            return self._diagnostic_result(
                source_info,
                "skipped",
                "paddle_not_ocr_target",
                runtime_metadata=_runtime_metadata(
                    device_diagnostics=device_diagnostics,
                    image_extension=suffix,
                    init_elapsed_ms=init_elapsed_ms,
                    ocr_elapsed_ms=ocr_elapsed_ms,
                    total_elapsed_ms=_elapsed_ms(total_started_at),
                    status="skipped",
                    diagnostic_code="paddle_not_ocr_target",
                ),
            )
        if suffix in self.pdf_extensions:
            return self._diagnostic_result(
                source_info,
                "failed",
                "paddle_pdf_not_supported",
                runtime_metadata=_runtime_metadata(
                    device_diagnostics=device_diagnostics,
                    image_extension=suffix,
                    init_elapsed_ms=init_elapsed_ms,
                    ocr_elapsed_ms=ocr_elapsed_ms,
                    total_elapsed_ms=_elapsed_ms(total_started_at),
                    status="failed",
                    diagnostic_code="paddle_pdf_not_supported",
                ),
            )
        if suffix not in self.ocr_extensions:
            return self._diagnostic_result(
                source_info,
                "failed",
                "unsupported_input_type",
                runtime_metadata=_runtime_metadata(
                    device_diagnostics=device_diagnostics,
                    image_extension=suffix,
                    init_elapsed_ms=init_elapsed_ms,
                    ocr_elapsed_ms=ocr_elapsed_ms,
                    total_elapsed_ms=_elapsed_ms(total_started_at),
                    status="failed",
                    diagnostic_code="unsupported_input_type",
                ),
            )

        try:
            if self._ocr_factory is None:
                device_diagnostics = get_paddle_device_diagnostics()
            init_started_at = perf_counter()
            ocr = self._build_ocr(
                use_textline_orientation=self.use_angle_cls,
                device_diagnostics=device_diagnostics,
            )
            init_elapsed_ms = _elapsed_ms(init_started_at)
        except PaddleOCRUnavailable as exc:
            init_elapsed_ms = init_elapsed_ms or _elapsed_ms(total_started_at)
            return self._diagnostic_result(
                source_info,
                "failed",
                exc.diagnostic_code,
                runtime_metadata=_runtime_metadata(
                    device_diagnostics=device_diagnostics,
                    image_extension=suffix,
                    init_elapsed_ms=init_elapsed_ms,
                    ocr_elapsed_ms=ocr_elapsed_ms,
                    total_elapsed_ms=_elapsed_ms(total_started_at),
                    status="failed",
                    diagnostic_code=exc.diagnostic_code,
                ),
            )
        except Exception as exc:
            init_elapsed_ms = init_elapsed_ms or _elapsed_ms(total_started_at)
            return self._diagnostic_result(
                source_info,
                "failed",
                "paddle_runtime_error",
                diagnostic_detail_code=_safe_exception_code(exc),
                runtime_metadata=_runtime_metadata(
                    device_diagnostics=device_diagnostics,
                    image_extension=suffix,
                    init_elapsed_ms=init_elapsed_ms,
                    ocr_elapsed_ms=ocr_elapsed_ms,
                    total_elapsed_ms=_elapsed_ms(total_started_at),
                    status="failed",
                    diagnostic_code="paddle_runtime_error",
                ),
            )

        path = source_info.get("file_path")
        if not isinstance(path, Path) or not path.exists():
            return self._diagnostic_result(
                source_info,
                "failed",
                "source_not_accessible",
                runtime_metadata=_runtime_metadata(
                    device_diagnostics=device_diagnostics,
                    image_extension=suffix,
                    init_elapsed_ms=init_elapsed_ms,
                    ocr_elapsed_ms=ocr_elapsed_ms,
                    total_elapsed_ms=_elapsed_ms(total_started_at),
                    status="failed",
                    diagnostic_code="source_not_accessible",
                ),
            )

        fallback_warning: str | None = None
        ocr_started_at = perf_counter()
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
                ocr_elapsed_ms = _elapsed_ms(ocr_started_at)
                return self._diagnostic_result(
                    source_info,
                    "failed",
                    "paddle_runtime_error",
                    diagnostic_detail_code=_safe_exception_code(fallback_exc or exc),
                    runtime_metadata=_runtime_metadata(
                        device_diagnostics=device_diagnostics,
                        image_extension=suffix,
                        init_elapsed_ms=init_elapsed_ms,
                        ocr_elapsed_ms=ocr_elapsed_ms,
                        total_elapsed_ms=_elapsed_ms(total_started_at),
                        status="failed",
                        diagnostic_code="paddle_runtime_error",
                    ),
                )
        except Exception as exc:
            if self.use_angle_cls and isinstance(exc, NotImplementedError):
                try:
                    fallback_init_started_at = perf_counter()
                    ocr = self._build_ocr(
                        use_textline_orientation=False,
                        device_diagnostics=device_diagnostics,
                    )
                    init_elapsed_ms += _elapsed_ms(fallback_init_started_at)
                    raw_result = self._run_ocr(ocr, path, use_textline_orientation=False)
                    fallback_warning = "paddle_textline_orientation_fallback"
                except Exception as fallback_exc:
                    ocr_elapsed_ms = _elapsed_ms(ocr_started_at)
                    return self._diagnostic_result(
                        source_info,
                        "failed",
                        "paddle_runtime_error",
                        diagnostic_detail_code=_safe_exception_code(fallback_exc),
                        runtime_metadata=_runtime_metadata(
                            device_diagnostics=device_diagnostics,
                            image_extension=suffix,
                            init_elapsed_ms=init_elapsed_ms,
                            ocr_elapsed_ms=ocr_elapsed_ms,
                            total_elapsed_ms=_elapsed_ms(total_started_at),
                            status="failed",
                            diagnostic_code="paddle_runtime_error",
                        ),
                    )
            else:
                ocr_elapsed_ms = _elapsed_ms(ocr_started_at)
                return self._diagnostic_result(
                    source_info,
                    "failed",
                    "paddle_runtime_error",
                    diagnostic_detail_code=_safe_exception_code(exc),
                    runtime_metadata=_runtime_metadata(
                        device_diagnostics=device_diagnostics,
                        image_extension=suffix,
                        init_elapsed_ms=init_elapsed_ms,
                        ocr_elapsed_ms=ocr_elapsed_ms,
                        total_elapsed_ms=_elapsed_ms(total_started_at),
                        status="failed",
                        diagnostic_code="paddle_runtime_error",
                    ),
                )

        sanitized_result = self._sanitize_result(raw_result)
        if not fallback_warning and _should_try_quality_normalization_fallback(sanitized_result):
            try:
                normalized_raw_result = self._run_ocr_with_normalized_image(
                    ocr,
                    path,
                    use_textline_orientation=self.use_angle_cls,
                )
                normalized_result = self._sanitize_result(normalized_raw_result)
                if _quality_score(normalized_result) > _quality_score(sanitized_result):
                    sanitized_result = normalized_result
                    fallback_warning = "paddle_image_quality_fallback"
            except Exception:
                sanitized_result.setdefault("warnings", [])
                sanitized_result["warnings"].append("paddle_image_quality_fallback_skipped")
        if not fallback_warning and _should_try_orientation_fallback(sanitized_result):
            try:
                rotated_result = self._best_rotated_image_result(
                    ocr,
                    path,
                    use_textline_orientation=self.use_angle_cls,
                )
                if rotated_result is not None and _quality_score(rotated_result) > _quality_score(sanitized_result):
                    sanitized_result = rotated_result
                    fallback_warning = "paddle_image_rotation_fallback"
            except Exception:
                sanitized_result.setdefault("warnings", [])
                sanitized_result["warnings"].append("paddle_image_rotation_fallback_skipped")
        supplemental_warnings: list[str] = []
        if _can_try_supplemental_fallback(fallback_warning) and _should_try_supplemental_image_fallback(sanitized_result):
            try:
                enhanced_result = self._best_enhanced_image_result(
                    ocr,
                    path,
                    use_textline_orientation=self.use_angle_cls,
                )
                if enhanced_result is not None:
                    merged_result = _merge_missing_candidate_hints(
                        sanitized_result,
                        enhanced_result,
                        allowed_types={"merchant_name", "business_number", "total_amount", "final_amount", "paid_amount"},
                    )
                    if _candidate_signature(merged_result) != _candidate_signature(sanitized_result):
                        sanitized_result = merged_result
                        supplemental_warnings.append("paddle_enhanced_image_candidate_fallback")
            except Exception:
                sanitized_result.setdefault("warnings", [])
                sanitized_result["warnings"].append("paddle_enhanced_image_candidate_fallback_skipped")
        if _can_try_supplemental_fallback(fallback_warning) and _should_try_supplemental_image_fallback(sanitized_result):
            try:
                detail_result = self._best_detail_crop_result(
                    ocr,
                    path,
                    use_textline_orientation=self.use_angle_cls,
                )
                if detail_result is not None:
                    merged_result = _merge_missing_candidate_hints(
                        sanitized_result,
                        detail_result,
                        allowed_types={"merchant_name", "business_number"},
                    )
                    if _candidate_signature(merged_result) != _candidate_signature(sanitized_result):
                        sanitized_result = merged_result
                        supplemental_warnings.append("paddle_detail_crop_candidate_fallback")
            except Exception:
                sanitized_result.setdefault("warnings", [])
                sanitized_result["warnings"].append("paddle_detail_crop_candidate_fallback_skipped")
        ocr_elapsed_ms = _elapsed_ms(ocr_started_at)
        if fallback_warning:
            sanitized_result.setdefault("warnings", [])
            sanitized_result["warnings"].append(fallback_warning)
        if supplemental_warnings:
            sanitized_result.setdefault("warnings", [])
            sanitized_result["warnings"].extend(supplemental_warnings)
        _apply_runtime_metadata(
            sanitized_result,
            _runtime_metadata(
                device_diagnostics=device_diagnostics,
                image_extension=suffix,
                init_elapsed_ms=init_elapsed_ms,
                ocr_elapsed_ms=ocr_elapsed_ms,
                total_elapsed_ms=_elapsed_ms(total_started_at),
                status="completed" if sanitized_result.get("status") in {"succeeded", "success", "completed"} else str(sanitized_result.get("status") or "failed"),
                diagnostic_code=_string_or_completed(sanitized_result.get("diagnostic_code")),
            ),
        )
        return self.adapter.convert(
            sanitized_result,
            source_file_id=str(source_info["source_file_id"]),
            source_file_name=str(source_info["source_file_name"]),
            provider_version=sanitized_result.get("engine_version") or "optional",
        )

    def _build_ocr(
        self,
        *,
        use_textline_orientation: bool,
        device_diagnostics: Mapping[str, Any] | None = None,
    ) -> Any:
        factory = self._ocr_factory
        if factory is not None:
            cached = self._ocr_instances.get(use_textline_orientation)
            if cached is not None:
                return cached
            return self._build_with_factory(factory, use_textline_orientation=use_textline_orientation)

        cache_key = _ocr_cache_key(
            lang=self.lang,
            use_textline_orientation=use_textline_orientation,
            use_gpu=self.use_gpu,
            show_log=self.show_log,
        )
        cached = _GLOBAL_OCR_INSTANCES.get(cache_key)
        if cached is not None:
            return cached

        if self.use_gpu and (device_diagnostics or {}).get("cuda_compiled") is False:
            raise PaddleOCRUnavailable("paddle_cuda_not_available")
        factory = _load_paddle_ocr_class()
        if importlib.util.find_spec("paddle") is None:
            raise PaddleOCRUnavailable("paddle_runtime_missing")
        ocr = self._build_with_factory(factory, use_textline_orientation=use_textline_orientation)
        _GLOBAL_OCR_INSTANCES[cache_key] = ocr
        return ocr

    def _build_with_factory(self, factory: Callable[..., Any], *, use_textline_orientation: bool) -> Any:
        try:
            ocr = factory(
                lang=self.lang,
                use_angle_cls=use_textline_orientation,
                use_gpu=self.use_gpu,
                show_log=self.show_log,
            )
        except TypeError:
            ocr = factory(**self._modern_factory_kwargs(use_textline_orientation=use_textline_orientation))
        self._ocr_instances[use_textline_orientation] = ocr
        return ocr

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

    def _best_rotated_image_result(
        self,
        ocr: Any,
        path: Path,
        *,
        use_textline_orientation: bool,
    ) -> dict[str, Any] | None:
        from PIL import Image, ImageOps

        best_result: dict[str, Any] | None = None
        best_score = -1
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with Image.open(path) as image:
                normalized = ImageOps.exif_transpose(image).convert("RGB")
                for angle in (90, 180, 270):
                    rotated_path = temp_path / f"paddle_rotated_{angle}.jpg"
                    normalized.rotate(angle, expand=True).save(rotated_path, format="JPEG")
                    raw_result = self._run_ocr(
                        ocr,
                        rotated_path,
                        use_textline_orientation=use_textline_orientation,
                    )
                    sanitized = self._sanitize_result(raw_result)
                    score = _quality_score(sanitized)
                    if score > best_score:
                        best_score = score
                        best_result = sanitized
        return best_result

    def _best_enhanced_image_result(
        self,
        ocr: Any,
        path: Path,
        *,
        use_textline_orientation: bool,
    ) -> dict[str, Any] | None:
        from PIL import Image, ImageEnhance, ImageOps

        best_result: dict[str, Any] | None = None
        best_score = -1
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with Image.open(path) as image:
                normalized = ImageOps.exif_transpose(image).convert("RGB")
                for angle in (0, 90, 180, 270):
                    rotated = normalized.rotate(angle, expand=True) if angle else normalized
                    enhanced = ImageEnhance.Contrast(ImageOps.grayscale(rotated)).enhance(1.8).convert("RGB")
                    enhanced_path = temp_path / f"paddle_enhanced_{angle}.jpg"
                    enhanced.save(enhanced_path, format="JPEG")
                    raw_result = self._run_ocr(
                        ocr,
                        enhanced_path,
                        use_textline_orientation=use_textline_orientation,
                    )
                    sanitized = self._sanitize_result(raw_result)
                    score = _quality_score(sanitized)
                    if score > best_score:
                        best_score = score
                        best_result = sanitized
        return best_result

    def _best_detail_crop_result(
        self,
        ocr: Any,
        path: Path,
        *,
        use_textline_orientation: bool,
    ) -> dict[str, Any] | None:
        from PIL import Image, ImageEnhance, ImageOps

        best_result: dict[str, Any] | None = None
        best_score = -1
        crop_specs = (
            (0.12, 0.22, 0.72, 0.34),
            (0.10, 0.20, 0.80, 0.40),
        )
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with Image.open(path) as image:
                normalized = ImageOps.exif_transpose(image).convert("RGB")
                for angle in (90, 270):
                    rotated = normalized.rotate(angle, expand=True)
                    width, height = rotated.size
                    for crop_index, (left, top, right, bottom) in enumerate(crop_specs):
                        box = (
                            int(width * left),
                            int(height * top),
                            int(width * right),
                            int(height * bottom),
                        )
                        crop = rotated.crop(box)
                        crop = crop.resize((max(crop.width * 3, 1), max(crop.height * 3, 1)))
                        crop = ImageEnhance.Contrast(crop).enhance(1.6)
                        crop_path = temp_path / f"paddle_detail_{angle}_{crop_index}.jpg"
                        crop.save(crop_path, format="JPEG")
                        raw_result = self._run_ocr(
                            ocr,
                            crop_path,
                            use_textline_orientation=use_textline_orientation,
                        )
                        sanitized = self._sanitize_result(raw_result)
                        score = _quality_score(sanitized)
                        if score > best_score:
                            best_score = score
                            best_result = sanitized
        return best_result

    def _modern_factory_kwargs(self, *, use_textline_orientation: bool) -> dict[str, Any]:
        return {
            "lang": self.lang,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": use_textline_orientation,
            "show_log": self.show_log,
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
        runtime_metadata: Mapping[str, Any] | None = None,
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
        if runtime_metadata:
            _apply_runtime_metadata(payload, runtime_metadata)
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


def get_paddle_device_diagnostics() -> dict[str, Any]:
    """Return non-sensitive Paddle runtime device diagnostics."""

    try:
        paddle = importlib.import_module("paddle")
        cuda_compiled = bool(paddle.device.is_compiled_with_cuda())
        device = _safe_device_token(paddle.device.get_device())
    except ImportError:
        return {
            "device": "unknown",
            "cuda_compiled": None,
            "diagnostic_code": "paddle_runtime_missing",
        }
    except Exception:
        return {
            "device": "unknown",
            "cuda_compiled": None,
            "diagnostic_code": "paddle_device_diagnostic_failed",
        }
    return {
        "device": device,
        "cuda_compiled": cuda_compiled,
        "diagnostic_code": None,
    }


def _unknown_paddle_device_diagnostics() -> dict[str, Any]:
    return {
        "device": "unknown",
        "cuda_compiled": None,
        "diagnostic_code": None,
    }


def _runtime_metadata(
    *,
    device_diagnostics: Mapping[str, Any],
    image_extension: str,
    init_elapsed_ms: int,
    ocr_elapsed_ms: int,
    total_elapsed_ms: int,
    status: str,
    diagnostic_code: str,
) -> dict[str, Any]:
    return {
        "provider": "paddle",
        "device": _safe_device_token(device_diagnostics.get("device")),
        "cuda_compiled": _optional_bool(device_diagnostics.get("cuda_compiled")),
        "image_extension": _safe_extension(image_extension),
        "init_elapsed_ms": _non_negative_int(init_elapsed_ms),
        "ocr_elapsed_ms": _non_negative_int(ocr_elapsed_ms),
        "total_elapsed_ms": _non_negative_int(total_elapsed_ms),
        "runtime_status": _safe_runtime_status(status),
        "runtime_diagnostic_code": _safe_diagnostic_code(diagnostic_code),
    }


def _apply_runtime_metadata(payload: dict[str, Any], metadata: Mapping[str, Any]) -> None:
    for key in (
        "provider",
        "device",
        "cuda_compiled",
        "image_extension",
        "init_elapsed_ms",
        "ocr_elapsed_ms",
        "total_elapsed_ms",
        "runtime_status",
        "runtime_diagnostic_code",
    ):
        if key in metadata:
            payload[key] = metadata[key]


def _elapsed_ms(started_at: float) -> int:
    return _non_negative_int(round((perf_counter() - started_at) * 1000))


def _ocr_cache_key(
    *,
    lang: str,
    use_textline_orientation: bool,
    use_gpu: bool,
    show_log: bool,
) -> tuple[str, bool, bool, bool]:
    return (str(lang or "korean").strip().lower() or "korean", use_textline_orientation, use_gpu, show_log)


def _safe_device_token(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    if not text:
        return "unknown"
    text = re.sub(r"[^a-z0-9:_-]", "_", text)
    return text[:40] or "unknown"


def _safe_extension(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text.startswith("."):
        text = f".{text}" if text else ""
    if re.fullmatch(r"\.[a-z0-9]{1,8}", text):
        return text
    return "unknown"


def _safe_runtime_status(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"completed", "failed", "partial", "skipped"}:
        return normalized
    if normalized in {"succeeded", "success"}:
        return "completed"
    return "failed"


def _safe_diagnostic_code(value: str) -> str:
    text = str(value or "completed").strip().lower()
    text = re.sub(r"[^a-z0-9_-]", "_", text)
    return text[:80] or "completed"


def _string_or_completed(value: Any) -> str:
    return _safe_diagnostic_code(str(value)) if value else "completed"


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _non_negative_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(number, 0)


def _clear_paddle_ocr_cache_for_tests() -> None:
    _GLOBAL_OCR_INSTANCES.clear()


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


def _should_try_quality_normalization_fallback(payload: Mapping[str, Any]) -> bool:
    lines = payload.get("lines")
    candidates = payload.get("key_value_candidates")
    line_count = len(lines) if isinstance(lines, list) else 0
    candidate_count = len(candidates) if isinstance(candidates, list) else 0
    return line_count < 60 or candidate_count < 3


def _should_try_orientation_fallback(payload: Mapping[str, Any]) -> bool:
    candidates = payload.get("key_value_candidates")
    candidate_items = candidates if isinstance(candidates, list) else []
    candidate_types = {
        str(candidate.get("candidate_type") or candidate.get("key") or "")
        for candidate in candidate_items
        if isinstance(candidate, Mapping)
    }
    reliable_types = {
        "merchant_name",
        "transaction_date",
        "business_number",
        "total_amount",
        "final_amount",
        "paid_amount",
        "payment_method",
    }
    return not bool(candidate_types & reliable_types)


def _should_try_supplemental_image_fallback(payload: Mapping[str, Any]) -> bool:
    candidates = payload.get("key_value_candidates")
    candidate_items = candidates if isinstance(candidates, list) else []
    candidate_types = {
        str(candidate.get("candidate_type") or candidate.get("key") or "")
        for candidate in candidate_items
        if isinstance(candidate, Mapping)
    }
    has_amount = bool(candidate_types & {"total_amount", "final_amount", "paid_amount"})
    has_merchant_anchor = bool(candidate_types & {"merchant_name", "business_number"})
    return not (has_amount and has_merchant_anchor)


def _can_try_supplemental_fallback(fallback_warning: str | None) -> bool:
    return fallback_warning != "paddle_image_normalization_fallback"


def _candidate_signature(payload: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    candidates = payload.get("key_value_candidates")
    candidate_items = candidates if isinstance(candidates, list) else []
    signature: list[tuple[str, str]] = []
    for candidate in candidate_items:
        if not isinstance(candidate, Mapping):
            continue
        candidate_type = str(candidate.get("candidate_type") or candidate.get("key") or "")
        value = str(candidate.get("normalized_value") or candidate.get("value") or "")
        if candidate_type and value:
            signature.append((candidate_type, value))
    return tuple(signature)


def _merge_missing_candidate_hints(
    primary: Mapping[str, Any],
    supplemental: Mapping[str, Any],
    *,
    allowed_types: set[str],
) -> dict[str, Any]:
    merged = dict(primary)
    primary_candidates = primary.get("key_value_candidates")
    supplemental_candidates = supplemental.get("key_value_candidates")
    merged_candidates = list(primary_candidates) if isinstance(primary_candidates, list) else []
    existing_types = {
        str(candidate.get("candidate_type") or candidate.get("key") or "")
        for candidate in merged_candidates
        if isinstance(candidate, Mapping)
    }
    for candidate in supplemental_candidates if isinstance(supplemental_candidates, list) else []:
        if not isinstance(candidate, Mapping):
            continue
        candidate_type = str(candidate.get("candidate_type") or candidate.get("key") or "")
        if candidate_type not in allowed_types or candidate_type in existing_types:
            continue
        value = str(candidate.get("normalized_value") or candidate.get("value") or "").strip()
        if not value or value == "[REDACTED]":
            continue
        merged_candidates.append(dict(candidate))
        existing_types.add(candidate_type)
    merged["key_value_candidates"] = merged_candidates
    return merged


def _quality_score(payload: Mapping[str, Any]) -> int:
    lines = payload.get("lines")
    candidates = payload.get("key_value_candidates")
    line_count = len(lines) if isinstance(lines, list) else 0
    candidate_items = candidates if isinstance(candidates, list) else []
    candidate_types = {
        str(candidate.get("candidate_type") or candidate.get("key") or "")
        for candidate in candidate_items
        if isinstance(candidate, Mapping)
    }
    core_types = {
        "merchant_name",
        "transaction_date",
        "business_number",
        "total_amount",
        "final_amount",
        "paid_amount",
        "supply_amount",
        "vat_amount",
        "payment_method",
    }
    amount_types = {
        "total_amount",
        "final_amount",
        "paid_amount",
        "supply_amount",
        "vat_amount",
    }
    return (
        min(line_count, 120) // 5
        + len(candidate_types & core_types) * 100
        + len(candidate_types & amount_types) * 25
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
    r"\b(?:\d{4}[-./]\d{1,2}[-./]\d{1,2}|\d{2}[-./]\d{1,2}[-./]\d{1,2}|\d{8})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?\b"
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
PAID_AMOUNT_LABELS = ("결제", "받은", "청구", "승인금액", "paid")
SUPPLY_LABELS = ("공급", "공급가", "공급가액", "과세물품가액", "물품가액", "물품가", "supply")
VAT_LABELS = ("부가", "세액", "vat", "tax")
DISCOUNT_LABELS = ("할인", "쿠폰", "차감", "discount")
GROSS_LABELS = ("상품금액", "매출", "공급대가", "gross")
PAYMENT_CARD_LABELS = ("카드", "신용", "체크", "card", "visa", "master", "일시불", "할부")
PAYMENT_CASH_LABELS = ("현금", "cash")
APPROVAL_NUMBER_LABELS = ("승인번호", "승인NO", "승인No", "승인 no", "approval_no", "approval number")
MERCHANT_LABELS = (
    "\uc0c1\ud638",
    "\uc0c1\ud638\uba85",
    "\ub9e4\uc7a5\uba85",
    "\uac00\ub9f9\uc810\uba85",
    "\uac00\ub9f9\uc810",
    "\uc810\ud3ec\uba85",
    "\uc0c1\uc810\uba85",
    "\uc0ac\uc5c5\uc7a5\uba85",
    "\uc5c5\uccb4\uba85",
    "\ub9e4\ucd9c\ucc98",
)
KOREAN_DATE_LABELS = (
    "\ub0a0\uc9dc",
    "\uc77c\uc2dc",
    "\uac70\ub798\uc77c",
    "\uac70\ub798\uc77c\uc2dc",
    "\ub9e4\ucd9c\uc77c",
    "\ub9e4\ucd9c\uc77c\uc2dc",
    "\uc2b9\uc778\uc77c",
    "\uc2b9\uc778\uc77c\uc2dc",
    "\ubc1c\ud589\uc77c",
    "\ubc1c\ud589\uc77c\uc2dc",
    "\uacb0\uc81c\ub0a0\uc9dc",
    "\uacb0\uc81c\ub0a0\uc9dc\ubc0f\uc2dc\uac04",
)
SIMPLE_TOTAL_AMOUNT_LABELS = (
    "\uae08\uc561",
    "\ucd1d\uc561",
    "\ud569\uacc4\uae08\uc561",
    "\uacb0\uc81c\uae08\uc561",
    "\uc2b9\uc778\uae08\uc561",
    "\uc774\uc6a9\uae08\uc561",
)
APP_SCREEN_MARKERS = (
    "\uce74\ud14c\uace0\ub9ac",
    "\ubbf8\uc9c0\uc815",
    "\uacb0\uc81c\uc815\ubcf4",
    "\uc601\uc218\uc99d",
    "\uacb0\uc81c\ucde8\uc18c",
)
APP_SCREEN_MERCHANT_BLOCKERS = (
    "\uc601\uc218\uc99d",
    "\uacb0\uc81c",
    "\ucde8\uc18c",
    "\uc815\ubcf4",
    "\ud3b8\uc9d1",
    "\uc0ad\uc81c",
    "\uce74\ud14c\uace0\ub9ac",
    "\ubbf8\uc9c0\uc815",
    "\ub0a0\uc9dc",
    "\uc77c\uc2dc",
    "\uce74\ub4dc",
    "\uc774\ub984",
    "\uc2b9\uc778",
    "\ubc88\ud638",
    "\uae08\uc561",
    "\ucd1d\uc561",
    "\uc624\uc804",
    "\uc624\ud6c4",
)
TOP_MERCHANT_SUFFIX_MARKERS = (
    "주유소",
    "식당",
    "카페",
    "커피",
    "김밥",
    "마트",
    "약국",
    "서점",
    "상회",
    "상사",
    "식품",
    "호텔",
    "리조트",
    "\uace0\uae43\uc9d1",
    "fresh",
)


def build_paddle_candidate_hints_from_safe_lines(lines: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build conservative candidates from already-sanitized PaddleOCR line rows."""
    return _candidate_hints_from_lines(lines)


def _candidate_hints_from_lines(lines: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_types: set[str] = set()

    _append_columnar_tax_summary_candidates(candidates, seen_types, lines)
    _append_compact_tax_amount_candidates(candidates, seen_types, lines)
    _append_top_tax_total_sequence_candidates(candidates, seen_types, lines)
    _append_labeled_tax_sum_sequence_candidates(candidates, seen_types, lines)
    _append_gas_split_tax_total_candidates(candidates, seen_types, lines)
    _append_card_receipt_zero_group_amount_candidates(candidates, seen_types, lines)
    _append_card_receipt_split_tax_summary_candidates(candidates, seen_types, lines)
    _append_split_total_label_amount_candidates(candidates, seen_types, lines)
    _append_card_sales_total_adjacent_amount_candidate(candidates, seen_types, lines)

    for index, line in enumerate(lines):
        text = _safe_line_text(line)
        if not text:
            continue
        source_block_id = str(line.get("block_id") or "")
        confidence = _optional_float(line.get("confidence"))

        date_text = (
            _joined_korean_date_fragment(lines, index)
            or _labeled_compact_datetime_fragment(lines, index)
            or _noisy_embedded_compact_datetime_fragment(lines, index)
            or _labeled_flexible_short_date_fragment(lines, index)
            or _labeled_short_date_fragment(lines, index)
            or _joined_date_fragment(lines, index)
            or text
        )
        date_match = DATE_CANDIDATE_PATTERN.search(date_text)
        if date_match and _is_valid_date_candidate(date_match.group(0)):
            _append_candidate(
                candidates,
                seen_types,
                candidate_type="transaction_date",
                key="transaction_date",
                value=date_match.group(0),
                source_block_id=source_block_id,
                confidence=confidence,
            )

        business_text = (
            _reverse_labeled_business_number_fragment(lines, index)
            or _labeled_business_number_prefix_fragment(lines, index)
            or _joined_business_number_fragment(lines, index)
            or text
        )
        business_match = BUSINESS_NUMBER_CANDIDATE_PATTERN.search(business_text)
        if (
            business_match
            and _has_valid_business_number_checksum(business_match.group(0))
            and not _looks_like_card_business_number_false_positive(lines, index, business_text)
        ):
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
        amount_label_compact = _compact_line_with_next(lines, index)
        labeled_merchant_name = _labeled_merchant_value(text) or _next_labeled_merchant_value(lines, index)
        merchant_name = labeled_merchant_name
        if not merchant_name:
            merchant_name = _business_block_merchant_value(lines, index)
        if not merchant_name:
            merchant_name = _app_screen_merchant_value(lines, index)
        if merchant_name:
            _append_candidate(
                candidates,
                seen_types,
                candidate_type="merchant_name",
                key="merchant_name",
                value=merchant_name,
                source_block_id=source_block_id,
                confidence=confidence,
            )
        if labeled_merchant_name:
            continue

        if _is_app_navigation_label(lines, index):
            continue

        approval_number = _labeled_approval_number_value(lines, index)
        if approval_number:
            _append_candidate(
                candidates,
                seen_types,
                candidate_type="approval_number",
                key="approval_number",
                value=approval_number,
                source_block_id=source_block_id,
                confidence=confidence,
            )

        split_vat_amount = _split_vat_amount_between_fragments(lines, index)
        if split_vat_amount is not None:
            _append_amount_candidate(candidates, seen_types, "vat_amount", split_vat_amount, source_block_id, confidence)
            continue

        if any(label in compact for label in PAYMENT_CARD_LABELS) or _has_split_card_marker(lines, index):
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

        if _has_blocking_non_amount_label(compact):
            continue
        amount = _last_reasonable_amount(text, allow_zero=_has_zero_safe_amount_label(compact))
        suppress_nearby_amount = False
        if amount is None and _has_zero_safe_amount_label(amount_label_compact):
            if _has_any_label(amount_label_compact, SUPPLY_LABELS):
                amount = _previous_tax_amount_if_balanced(lines, index)
                if amount is None:
                    amount = _nearby_split_amount_fragments(lines, index, max_lines=4)
            elif _has_any_label(amount_label_compact, VAT_LABELS) and _is_split_vat_label(compact, amount_label_compact):
                amount = _previous_vat_amount_if_balanced(lines, index)
                suppress_nearby_amount = amount is None
            elif _has_any_label(amount_label_compact, VAT_LABELS) and _next_nonempty_has_label(lines, index, SUPPLY_LABELS):
                suppress_nearby_amount = True
            elif _has_any_label(amount_label_compact, VAT_LABELS):
                amount = _previous_vat_amount_if_balanced(lines, index)
            elif _has_simple_total_amount_label(amount_label_compact):
                amount = _nearby_currency_split_amount(lines, index, max_lines=3)
                if amount is None:
                    amount = _nearby_split_amount_fragments(lines, index, max_lines=3)
            prefer_largest_nearby = (
                _is_standalone_total_label(compact)
                or _has_any_label(amount_label_compact, FINAL_LABELS)
                or _has_any_label(amount_label_compact, TOTAL_LABELS)
                or _has_simple_total_amount_label(amount_label_compact)
            )
            if amount is None and prefer_largest_nearby:
                if _is_standalone_total_label(compact):
                    amount = _split_amount_around_label(lines, index)
                    if amount is None:
                        amount = _nearby_labeled_amount(lines, index, allow_zero=True, max_lines=1)
                    if amount is None:
                        amount = _nearby_split_amount_fragments(lines, index, max_lines=3)
                    if amount is None:
                        amount = _previous_standalone_amount(lines, index, max_lines=4)
                if amount is None:
                    amount = _previous_split_amount_fragments(lines, index, max_lines=3)
        if amount is None and _has_zero_safe_amount_label(amount_label_compact) and not suppress_nearby_amount:
            amount = _nearby_labeled_amount(
                lines,
                index,
                allow_zero=True,
                max_lines=10 if prefer_largest_nearby else 4,
                prefer_largest=prefer_largest_nearby,
            )
        if amount is None and _has_inline_card_amount_label(compact):
            amount = _nearby_split_amount_fragments(lines, index, max_lines=3)
        if amount is None:
            continue
        if _has_any_label(amount_label_compact, SUPPLY_LABELS):
            _append_amount_candidate(candidates, seen_types, "supply_amount", amount, source_block_id, confidence)
        elif _has_any_label(amount_label_compact, VAT_LABELS):
            if not _is_implausible_vat_amount(candidates, amount):
                _append_amount_candidate(candidates, seen_types, "vat_amount", amount, source_block_id, confidence)
        elif _has_any_label(amount_label_compact, DISCOUNT_LABELS):
            if not _is_discount_identifier_context(lines, index):
                _append_amount_candidate(candidates, seen_types, "discount_amount", amount, source_block_id, confidence)
        elif _has_any_label(amount_label_compact, GROSS_LABELS):
            _append_amount_candidate(candidates, seen_types, "gross_amount", amount, source_block_id, confidence)
        elif _has_paid_amount_label(amount_label_compact) or _has_inline_card_amount_label(compact):
            _append_amount_candidate(candidates, seen_types, "paid_amount", amount, source_block_id, confidence)
            _append_amount_candidate(candidates, seen_types, "total_amount", amount, source_block_id, confidence)
        elif _has_simple_total_amount_label(amount_label_compact):
            _append_amount_candidate(candidates, seen_types, "final_amount", amount, source_block_id, confidence)
            _append_amount_candidate(candidates, seen_types, "total_amount", amount, source_block_id, confidence)
        elif _is_standalone_total_label(compact) or _has_any_label(amount_label_compact, FINAL_LABELS):
            _append_amount_candidate(candidates, seen_types, "final_amount", amount, source_block_id, confidence)
            _append_amount_candidate(candidates, seen_types, "total_amount", amount, source_block_id, confidence)

    _append_top_known_merchant_candidate(candidates, seen_types, lines)
    _append_multiline_known_merchant_candidate(candidates, seen_types, lines)
    _append_top_card_slip_amount_candidates(candidates, seen_types, lines)
    _append_repeated_card_slip_amount_candidates(candidates, seen_types, lines)
    _append_sum_checked_total_amount_candidates(candidates, seen_types, lines)
    _append_card_receipt_won_amount_candidates(candidates, seen_types, lines)
    _append_card_receipt_tax_adjacent_amount_candidates(candidates, seen_types, lines)
    _normalize_contextual_merchant_candidates(candidates, lines)
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


def _append_columnar_tax_summary_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    for index in range(0, max(len(lines) - 2, 0)):
        supply_text = _safe_line_text(lines[index]) or ""
        total_text = _safe_line_text(lines[index + 1]) or ""
        vat_text = _safe_line_text(lines[index + 2]) or ""
        supply_compact = _compact_line(supply_text)
        total_compact = _compact_line(total_text)
        vat_compact = _compact_line(vat_text)
        if not (
            _has_any_label(supply_compact, SUPPLY_LABELS)
            and (_has_any_label(total_compact, TOTAL_LABELS) or _has_any_label(total_compact, FINAL_LABELS))
            and _has_any_label(vat_compact, VAT_LABELS)
        ):
            continue
        amounts = _tax_summary_amount_sequence(lines, index + 3, max_lines=8)
        if amounts is None:
            continue
        vat_amount, supply_amount, total_amount = amounts
        confidence = _optional_float(lines[index].get("confidence"))
        source_block_id = str(lines[index].get("block_id") or "")
        _append_amount_candidate(candidates, seen_types, "vat_amount", vat_amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "supply_amount", supply_amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "final_amount", total_amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "total_amount", total_amount, source_block_id, confidence)
        return


def _append_compact_tax_amount_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    for index, line in enumerate(lines[:80]):
        text = _safe_line_text(line)
        if not text:
            continue
        compact = _compact_line(text)
        if "매출" not in compact:
            continue
        fragments: list[str] = []
        for nearby_index in range(index + 1, min(index + 5, len(lines))):
            candidate_text = _safe_line_text(lines[nearby_index])
            if not candidate_text:
                continue
            fragment = _amount_fragment_digits(candidate_text, allow_zero_group=True)
            if fragment is None and not fragments:
                first_fragment = re.sub(r"\D", "", candidate_text)
                if re.fullmatch(r"[1-9]\d{0,2}", first_fragment):
                    fragment = first_fragment
            if fragment is None:
                if fragments:
                    break
                continue
            fragments.append(fragment)
            if len(fragments) >= 3:
                break
        if len(fragments) < 3 or len(fragments[1]) != 3:
            continue
        supply_amount = int(f"{fragments[0]}{fragments[1]}")
        vat_amount = int(fragments[2])
        total_amount = supply_amount + vat_amount
        if supply_amount < 1_000 or vat_amount < 100 or total_amount > 1_000_000:
            continue
        if abs(round(supply_amount / 10) - vat_amount) > 2:
            continue
        source_block_id = str(line.get("block_id") or "")
        confidence = _optional_float(line.get("confidence"))
        _append_amount_candidate(candidates, seen_types, "supply_amount", supply_amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "vat_amount", vat_amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "final_amount", total_amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "total_amount", total_amount, source_block_id, confidence)
        return


def _append_top_tax_total_sequence_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if {"total_amount", "final_amount"} & seen_types:
        return
    amount_rows = _standalone_amount_rows_with_index(lines[:8])
    if len(amount_rows) < 3:
        return
    amount_rows = sorted(amount_rows, key=lambda item: item[3])
    for offset in range(0, len(amount_rows) - 2):
        total_amount, source_block_id, confidence, total_index = amount_rows[offset]
        supply_amount, _, _, supply_index = amount_rows[offset + 1]
        vat_amount, _, _, vat_index = amount_rows[offset + 2]
        if not (total_index < supply_index < vat_index):
            continue
        if total_amount < 1_000 or total_amount > 1_000_000:
            continue
        if supply_amount < 1_000 or vat_amount < 100:
            continue
        if abs((supply_amount + vat_amount) - total_amount) > 2:
            continue
        if abs(round(supply_amount / 10) - vat_amount) > 2:
            continue
        _append_amount_candidate(candidates, seen_types, "supply_amount", supply_amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "vat_amount", vat_amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "final_amount", total_amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "total_amount", total_amount, source_block_id, confidence)
        if _has_card_evidence(lines):
            _append_amount_candidate(candidates, seen_types, "paid_amount", total_amount, source_block_id, confidence)
        return


def _append_labeled_tax_sum_sequence_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if {"total_amount", "final_amount"} & seen_types:
        return
    amount_rows: list[tuple[int, str, float | None, int]] = []
    for index, line in enumerate(lines[:100]):
        text = _safe_line_text(line)
        if not text or not _is_standalone_amount_line(text):
            continue
        amount = _last_reasonable_amount(text)
        if amount is None or amount < 100:
            continue
        if _looks_like_pos_identifier_amount(lines, index, amount):
            continue
        amount_rows.append((amount, str(line.get("block_id") or ""), _optional_float(line.get("confidence")), index))
    if len(amount_rows) < 3:
        return
    amount_rows = sorted(amount_rows, key=lambda item: item[3])
    for first_offset in range(0, len(amount_rows) - 2):
        supply_amount, source_block_id, confidence, supply_index = amount_rows[first_offset]
        for second_offset in range(first_offset + 1, min(first_offset + 5, len(amount_rows) - 1)):
            vat_amount, _, _, vat_index = amount_rows[second_offset]
            for third_offset in range(second_offset + 1, min(second_offset + 5, len(amount_rows))):
                total_amount, _, _, total_index = amount_rows[third_offset]
                if total_index - supply_index > 12:
                    continue
                if supply_amount < 1_000 or vat_amount < 100 or total_amount < 1_000:
                    continue
                if abs((supply_amount + vat_amount) - total_amount) > 2:
                    continue
                if abs(round(supply_amount / 10) - vat_amount) > 2:
                    continue
                nearby_text = " ".join(
                    _safe_line_text(lines[nearby_index]) or ""
                    for nearby_index in range(max(supply_index - 4, 0), min(total_index + 5, len(lines)))
                )
                nearby_compact = _compact_line(nearby_text)
                if not (
                    any(label in nearby_compact for label in ("\ubd80\uac00\uc138", "\uac00\uc138", "\uc138\uc561"))
                    and any(label in nearby_compact for label in ("\ud310\ub9e4", "\uae08\uc561", "\ud569\uacc4", "\uc2b9\uc778"))
                ):
                    continue
                _append_amount_candidate(candidates, seen_types, "supply_amount", supply_amount, source_block_id, confidence)
                _append_amount_candidate(candidates, seen_types, "vat_amount", vat_amount, source_block_id, confidence)
                _append_amount_candidate(candidates, seen_types, "final_amount", total_amount, source_block_id, confidence)
                _append_amount_candidate(candidates, seen_types, "total_amount", total_amount, source_block_id, confidence)
                if _has_card_evidence(lines):
                    _append_amount_candidate(candidates, seen_types, "paid_amount", total_amount, source_block_id, confidence)
                return


def _append_gas_split_tax_total_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if {"total_amount", "final_amount"} & seen_types:
        return
    document_compact = _compact_line(" ".join(_safe_line_text(line) or "" for line in lines[:80]))
    if not any(token in document_compact for token in ("\uc8fc\uc720", "\ud718\ubc1c", "\uacbd\uc720")):
        return
    for supply_index, line in enumerate(lines[:80]):
        supply_text = _safe_line_text(line) or ""
        supply_digits = re.sub(r"\D", "", supply_text)
        if not re.fullmatch(r"[1-9]\d{5}", supply_digits):
            continue
        supply_amount = int(supply_digits)
        vat_options = _split_amount_options_before_index(lines, supply_index, min_prefix_digits=1, max_prefix_digits=2)
        total_options = _split_amount_options_before_index(lines, supply_index, min_prefix_digits=2, max_prefix_digits=3)
        if not vat_options or not total_options:
            continue
        matched_amounts = None
        for vat_amount, vat_index in vat_options:
            for total_amount, total_index in total_options:
                if total_index >= vat_index:
                    continue
                if abs((supply_amount + vat_amount) - total_amount) > 2:
                    continue
                if abs(round(supply_amount / 10) - vat_amount) > 2:
                    continue
                matched_amounts = (vat_amount, total_amount, total_index)
                break
            if matched_amounts is not None:
                break
        if matched_amounts is None:
            continue
        vat_amount, total_amount, total_index = matched_amounts
        nearby_text = " ".join(
            _safe_line_text(lines[nearby_index]) or ""
            for nearby_index in range(max(total_index - 5, 0), min(supply_index + 5, len(lines)))
        )
        nearby_compact = _compact_line(nearby_text)
        if not any(label in nearby_compact for label in ("\uae08\uc561", "\ubd80\uac00\uc138", "\uacfc\uc138")):
            continue
        source_block_id = str(line.get("block_id") or "")
        confidence = _optional_float(line.get("confidence"))
        _append_amount_candidate(candidates, seen_types, "supply_amount", supply_amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "vat_amount", vat_amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "final_amount", total_amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "total_amount", total_amount, source_block_id, confidence)
        if _has_card_evidence(lines):
            _append_amount_candidate(candidates, seen_types, "paid_amount", total_amount, source_block_id, confidence)
        return


def _split_amount_before_index(
    lines: list[Mapping[str, Any]],
    end_index: int,
    *,
    min_prefix_digits: int,
    max_prefix_digits: int,
) -> tuple[int, int] | None:
    for zero_index in range(end_index - 1, max(end_index - 10, -1), -1):
        zero_text = _safe_line_text(lines[zero_index]) or ""
        zero_fragment = _amount_fragment_digits(zero_text, allow_zero_group=True)
        if zero_fragment is None or not re.fullmatch(r"0{2,3}", zero_fragment):
            continue
        for prefix_index in range(zero_index - 1, max(zero_index - 5, -1), -1):
            prefix_text = _safe_line_text(lines[prefix_index]) or ""
            prefix_fragment = _amount_fragment_digits(prefix_text, allow_zero_group=False)
            if prefix_fragment is None:
                continue
            if not re.fullmatch(rf"[1-9]\d{{{min_prefix_digits - 1},{max_prefix_digits - 1}}}", prefix_fragment):
                continue
            amount = int(f"{prefix_fragment}{zero_fragment}")
            if amount >= 100:
                return amount, prefix_index
    return None


def _split_amount_options_before_index(
    lines: list[Mapping[str, Any]],
    end_index: int,
    *,
    min_prefix_digits: int,
    max_prefix_digits: int,
) -> list[tuple[int, int]]:
    options: list[tuple[int, int]] = []
    for suffix_index in range(end_index - 1, max(end_index - 10, -1), -1):
        suffix_text = _safe_line_text(lines[suffix_index]) or ""
        suffix_fragment = _amount_fragment_digits(suffix_text, allow_zero_group=True)
        if suffix_fragment is None or not re.fullmatch(r"\d{3}", suffix_fragment):
            continue
        for prefix_index in range(suffix_index - 1, max(suffix_index - 5, -1), -1):
            prefix_text = _safe_line_text(lines[prefix_index]) or ""
            prefix_fragment = _amount_fragment_digits(prefix_text, allow_zero_group=False)
            if prefix_fragment is None:
                continue
            if not re.fullmatch(rf"[1-9]\d{{{min_prefix_digits - 1},{max_prefix_digits - 1}}}", prefix_fragment):
                continue
            amount = int(f"{prefix_fragment}{suffix_fragment}")
            if amount >= 100:
                options.append((amount, prefix_index))
    return options


def _append_card_receipt_zero_group_amount_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if {"total_amount", "final_amount", "paid_amount"} & seen_types:
        return
    if not _has_card_evidence(lines):
        return
    label_index = None
    for index, line in enumerate(lines[:80]):
        compact = _compact_line(_safe_line_text(line) or "")
        if "거래금액" in compact or "총합계" in compact:
            label_index = index
            break
    if label_index is None:
        return
    for zero_index in range(label_index + 1, min(label_index + 18, len(lines))):
        zero_text = _safe_line_text(lines[zero_index]) or ""
        zero_fragment = _ocr_zero_group_fragment(zero_text)
        if zero_fragment is None:
            continue
        amount_options: list[tuple[int, int, str]] = []
        for prefix_index in range(zero_index - 1, max(zero_index - 4, label_index), -1):
            prefix_text = _safe_line_text(lines[prefix_index]) or ""
            prefix_fragment = _amount_fragment_digits(prefix_text, allow_zero_group=False)
            if prefix_fragment is None:
                continue
            if not re.fullmatch(r"[1-9]\d{0,2}", prefix_fragment):
                continue
            amount = int(f"{prefix_fragment}{zero_fragment}")
            if amount < 1000 or amount > 1_000_000:
                continue
            amount_options.append((amount, zero_index - prefix_index, "previous"))
        for prefix_index in range(zero_index + 1, min(zero_index + 4, len(lines))):
            prefix_text = _safe_line_text(lines[prefix_index]) or ""
            prefix_fragment = _amount_fragment_digits(prefix_text, allow_zero_group=False)
            if prefix_fragment is None:
                continue
            if not re.fullmatch(r"[1-9]\d{0,2}", prefix_fragment):
                continue
            amount = int(f"{prefix_fragment}{zero_fragment}")
            if amount < 1000 or amount > 1_000_000:
                continue
            amount_options.append((amount, prefix_index - zero_index, "next"))
        if amount_options:
            amount, _, _ = sorted(
                amount_options,
                key=lambda option: (
                    option[0] > 300_000,
                    option[1],
                    option[0],
                    0 if option[2] == "previous" else 1,
                ),
            )[0]
            source_block_id = str(lines[zero_index].get("block_id") or lines[label_index].get("block_id") or "")
            confidence = _optional_float(lines[zero_index].get("confidence"))
            for candidate_type in ("final_amount", "paid_amount", "total_amount"):
                _append_amount_candidate(candidates, seen_types, candidate_type, amount, source_block_id, confidence)
            return


def _append_card_receipt_tax_adjacent_amount_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if {"total_amount", "final_amount", "paid_amount"} & seen_types:
        return
    if not _has_card_evidence(lines):
        return
    for index, line in enumerate(lines[:90]):
        text = _safe_line_text(line) or ""
        if ":" in text:
            continue
        current_compact = _compact_line(text).upper()
        if any(
            token in current_compact
            for token in (
                "\ubd80\uac00\uc138",
                "\uc138\uc561",
                "\uacf5\uae09\uac00",
                "\uacf5\uae09\uac00\uc561",
            )
        ):
            continue
        digits = re.sub(r"\D", "", text)
        if not re.fullmatch(r"[1-9]\d{3,5}", digits):
            continue
        if digits.startswith(("2024", "2025", "2026", "2027")):
            continue
        amount = int(digits)
        if amount < 1_000 or amount > 300_000:
            continue
        if amount % 1_000 != 0:
            continue
        preceding_text = " ".join(
            _safe_line_text(lines[nearby_index]) or ""
            for nearby_index in range(max(index - 6, 0), index)
        )
        preceding_compact = _compact_line(preceding_text).lower()
        if not any(token in preceding_compact for token in ("승인", "visa", "master", "일시불", "할부", "fdi")):
            continue
        following_text = " ".join(
            _safe_line_text(lines[nearby_index]) or ""
            for nearby_index in range(index + 1, min(index + 6, len(lines)))
        )
        following_compact = _compact_line(following_text).upper()
        if not any(
            token in following_compact
            for token in (
                "\uac00\uc138",
                "\ubd80\uac00\uc138",
                "\uc138\uc561",
                "\uacf5\uae09\uac00",
                "\uacf5\uae09\uac00\uc561",
            )
        ):
            continue
        source_block_id = str(line.get("block_id") or "")
        confidence = _optional_float(line.get("confidence"))
        for candidate_type in ("final_amount", "paid_amount", "total_amount"):
            _append_amount_candidate(candidates, seen_types, candidate_type, amount, source_block_id, confidence)
        return


def _append_card_receipt_won_amount_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if {"total_amount", "final_amount", "paid_amount"} & seen_types:
        return
    if not _has_card_evidence(lines):
        return
    for index, line in enumerate(lines[:100]):
        text = _safe_line_text(line) or ""
        compact = _compact_line(text)
        if "\uc6d0" not in compact:
            continue
        if ":" in text or _has_blocking_non_amount_label(compact):
            continue
        digits = re.sub(r"\D", "", text)
        if not re.fullmatch(r"[1-9]\d{3,5}", digits):
            continue
        amount = int(digits)
        if amount < 1_000 or amount > 300_000:
            continue
        preceding_text = " ".join(
            _safe_line_text(lines[nearby_index]) or ""
            for nearby_index in range(max(index - 10, 0), index)
        )
        preceding_compact = _compact_line(preceding_text).lower()
        if not any(token in preceding_compact for token in ("신용카드", "카드", "visa", "master")):
            continue
        source_block_id = str(line.get("block_id") or "")
        confidence = _optional_float(line.get("confidence"))
        for candidate_type in ("final_amount", "paid_amount", "total_amount"):
            _append_amount_candidate(candidates, seen_types, candidate_type, amount, source_block_id, confidence)
        return


def _ocr_zero_group_fragment(text: str) -> str | None:
    compact = re.sub(r"[^0-9A-Za-zㅇ공]", "", str(text or "")).upper()
    if not compact:
        return None
    translated = compact.translate(str.maketrans({"O": "0", "C": "0", "ㅇ": "0", "공": "0"}))
    if re.fullmatch(r"0{2,3}", translated):
        return "0" * len(translated)
    return None


def _append_top_known_merchant_candidate(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if "merchant_name" in seen_types:
        return
    for index, line in enumerate(lines[:6]):
        merchant_name = _top_known_merchant_value(lines, index)
        if not merchant_name:
            continue
        _append_candidate(
            candidates,
            seen_types,
            candidate_type="merchant_name",
            key="merchant_name",
            value=merchant_name,
            source_block_id=str(line.get("block_id") or ""),
            confidence=_optional_float(line.get("confidence")),
        )
        return


def _append_multiline_known_merchant_candidate(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if "merchant_name" in seen_types:
        return
    for index in range(0, min(len(lines), 40)):
        source_line = lines[index]
        source_text = _safe_line_text(source_line)
        if not source_text:
            continue
        parts: list[str] = []
        for nearby_index in range(index, min(index + 4, len(lines))):
            text = _safe_line_text(lines[nearby_index])
            if not text:
                continue
            compact = _compact_line(text)
            if (
                DATE_CANDIDATE_PATTERN.search(text)
                or BUSINESS_NUMBER_CANDIDATE_PATTERN.search(text)
                or PHONE_LIKE_PATTERN.search(text)
                or CARD_LIKE_PATTERN.search(text)
                or _last_reasonable_amount(text) is not None
                or _has_blocking_non_amount_label(compact)
            ):
                break
            parts.append(text)
            combined = " ".join(parts)
            merchant_name = find_merchant_by_name_fragment(combined)
            if not merchant_name:
                continue
            _append_candidate(
                candidates,
                seen_types,
                candidate_type="merchant_name",
                key="merchant_name",
                value=merchant_name,
                source_block_id=str(source_line.get("block_id") or ""),
                confidence=_optional_float(source_line.get("confidence")),
            )
            return


def _normalize_contextual_merchant_candidates(
    candidates: list[dict[str, Any]],
    lines: list[Mapping[str, Any]],
) -> None:
    merchant_candidate = next(
        (candidate for candidate in candidates if candidate.get("candidate_type") == "merchant_name"),
        None,
    )
    if not merchant_candidate:
        return
    merchant_value = str(merchant_candidate.get("normalized_value") or merchant_candidate.get("value") or "")
    merchant_compact = _compact_line(merchant_value)
    if merchant_compact != "프라자주유소":
        return
    nearby_known = next(
        (
            known
            for known in (find_merchant_by_name_fragment(_safe_line_text(line)) for line in lines[:12])
            if known
        ),
        None,
    )
    if nearby_known and "현대오일뱅크" in nearby_known:
        merchant_candidate["value"] = nearby_known
        merchant_candidate["normalized_value"] = nearby_known


def _tax_summary_amount_sequence(lines: list[Mapping[str, Any]], start_index: int, *, max_lines: int) -> tuple[int, int, int] | None:
    fragments: list[str] = []
    for nearby_index in range(start_index, min(start_index + max_lines, len(lines))):
        text = _safe_line_text(lines[nearby_index])
        if not text:
            continue
        compact = _compact_line(text)
        if _has_blocking_non_amount_label(compact):
            break
        fragment = _amount_fragment_digits(text, allow_zero_group=True)
        if fragment is None:
            amount = _last_reasonable_amount(text)
            if amount is not None and amount >= 1_000 and not fragments:
                fragments.append(str(amount))
                continue
            if fragments:
                break
            continue
        fragments.append(fragment)
        if len(fragments) >= 5:
            break
    if len(fragments) < 5:
        return None
    vat_amount = int(fragments[0])
    supply_amount = int(f"{fragments[1]}{fragments[2]}")
    total_amount = int(f"{fragments[3]}{fragments[4]}")
    if vat_amount < 100 or supply_amount < 1_000 or total_amount < 1_000:
        return None
    if supply_amount + vat_amount != total_amount:
        return None
    return vat_amount, supply_amount, total_amount


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


def _is_implausible_vat_amount(candidates: list[dict[str, Any]], amount: int) -> bool:
    total_amount = _existing_amount_candidate(candidates, "total_amount")
    if total_amount is None:
        total_amount = _existing_amount_candidate(candidates, "final_amount")
    return total_amount is not None and amount >= total_amount


def _existing_amount_candidate(candidates: list[dict[str, Any]], candidate_type: str) -> int | None:
    for candidate in candidates:
        if candidate.get("candidate_type") != candidate_type:
            continue
        try:
            return int(str(candidate.get("normalized_value") or candidate.get("value") or ""))
        except ValueError:
            return None
    return None


def _append_repeated_card_slip_amount_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if {"total_amount", "final_amount", "paid_amount"} & seen_types:
        return
    has_payment_evidence = "payment_method" in seen_types or _has_card_evidence(lines)
    has_top_repeated_amount = _has_top_repeated_amount(lines)
    has_strong_repeated_amount = has_payment_evidence and _has_strong_repeated_amount(lines)
    has_repeated_split_amount = has_payment_evidence and _has_repeated_split_amount(lines)
    single_card_split_amount = _card_labeled_split_amount(lines)
    has_single_card_split_amount = single_card_split_amount is not None
    if has_single_card_split_amount:
        has_payment_evidence = True
    if (
        not has_top_repeated_amount
        and not has_strong_repeated_amount
        and not has_repeated_split_amount
        and not has_single_card_split_amount
    ):
        return

    repeated = _repeated_standalone_amount(lines)
    if repeated is None and single_card_split_amount is not None:
        repeated = single_card_split_amount
    if repeated is None:
        return
    amount, source_block_id, confidence = repeated
    candidate_types = ["final_amount", "total_amount"]
    if has_payment_evidence:
        candidate_types.insert(1, "paid_amount")
    for candidate_type in candidate_types:
        _append_amount_candidate(
            candidates,
            seen_types,
            candidate_type,
            amount,
            source_block_id,
            confidence,
        )


def _append_top_card_slip_amount_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if {"total_amount", "paid_amount"} & seen_types:
        return
    first_card_index = _first_card_evidence_index(lines)
    if first_card_index is None or first_card_index > 10:
        return
    top_amount = _top_standalone_amount(lines)
    if top_amount is None:
        return
    amount, source_block_id, confidence, _ = top_amount
    for candidate_type in ("paid_amount", "total_amount"):
        _append_amount_candidate(
            candidates,
            seen_types,
            candidate_type,
            amount,
            source_block_id,
            confidence,
        )


def _append_sum_checked_total_amount_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if {"total_amount", "final_amount"} & seen_types:
        return
    label_index = _first_total_label_index(lines)
    if label_index is None:
        return
    amount_rows = _standalone_amount_rows(lines[:label_index])
    if len(amount_rows) < 3:
        return

    total_amount, source_block_id, confidence = amount_rows[0]
    component_sum = sum(amount for amount, _, _ in amount_rows[1:])
    if total_amount != component_sum:
        return
    for candidate_type in ("final_amount", "total_amount"):
        _append_amount_candidate(
            candidates,
            seen_types,
            candidate_type,
            total_amount,
            source_block_id,
            confidence,
        )


def _append_split_total_label_amount_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if {"total_amount", "final_amount"} & seen_types:
        return
    for index in range(0, min(len(lines) - 3, 120)):
        text = _safe_line_text(lines[index])
        next_text = _safe_line_text(lines[index + 1])
        if not text or not next_text:
            continue
        compact = _compact_line(text).strip(":")
        next_compact = _compact_line(next_text).strip(":")
        if not (compact in {"\ud569\uacc4", "\ucd1d\uc561"} and next_compact in {"\uae08\uc561", "\uc561"}):
            continue
        amount = _nearby_split_amount_fragments(lines, index + 1, max_lines=3)
        if amount is None:
            amount = _nearby_labeled_amount(lines, index + 1, max_lines=3, prefer_largest=True)
        if amount is None or amount < 1_000:
            continue
        source_block_id = str(lines[index].get("block_id") or "")
        confidence = _optional_float(lines[index].get("confidence"))
        _append_amount_candidate(candidates, seen_types, "final_amount", amount, source_block_id, confidence)
        _append_amount_candidate(candidates, seen_types, "total_amount", amount, source_block_id, confidence)
        return


def _append_card_sales_total_adjacent_amount_candidate(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if {"total_amount", "final_amount", "paid_amount"} & seen_types:
        return
    if not _has_card_evidence(lines):
        return
    for index in range(0, min(len(lines), 120)):
        text = _safe_line_text(lines[index])
        if not text or not _is_standalone_amount_line(text):
            continue
        amount = _last_reasonable_amount(text)
        if amount is None or amount < 1_000:
            continue
        if _looks_like_pos_identifier_amount(lines, index, amount):
            continue
        nearby_compact = _compact_line(
            " ".join(_safe_line_text(lines[nearby_index]) or "" for nearby_index in range(index + 1, min(index + 4, len(lines))))
        )
        if not ("\ub9e4\ucd9c\ud569\uacc4" in nearby_compact and "\uce74\ub4dc" in nearby_compact):
            continue
        source_block_id = str(lines[index].get("block_id") or "")
        confidence = _optional_float(lines[index].get("confidence"))
        for candidate_type in ("paid_amount", "final_amount", "total_amount"):
            _append_amount_candidate(candidates, seen_types, candidate_type, amount, source_block_id, confidence)
        return


def _append_card_receipt_split_tax_summary_candidates(
    candidates: list[dict[str, Any]],
    seen_types: set[str],
    lines: list[Mapping[str, Any]],
) -> None:
    if {"total_amount", "final_amount", "paid_amount"} & seen_types:
        return
    if not _has_card_evidence(lines):
        return
    for index, line in enumerate(lines[:100]):
        text = _safe_line_text(line) or ""
        compact = _compact_line(text)
        if "\uc6d0" not in compact:
            continue
        digits = re.sub(r"\D", "", text)
        if not re.fullmatch(r"[1-9]\d{4,5}", digits):
            continue
        observed_amount = int(digits)
        corrected_total = observed_amount * 10
        if corrected_total < 100_000 or corrected_total > 1_000_000:
            continue
        split_amounts = _split_tax_amount_options_near_total(lines, index)
        for supply_amount in split_amounts:
            if supply_amount < 100_000 or supply_amount >= corrected_total:
                continue
            for vat_amount in split_amounts:
                if vat_amount < 10_000 or vat_amount >= supply_amount:
                    continue
                if abs(round(supply_amount / 10) - vat_amount) > 2:
                    continue
                if abs((supply_amount + vat_amount) - corrected_total) > 2:
                    continue
                source_block_id = str(line.get("block_id") or "")
                confidence = _optional_float(line.get("confidence"))
                _append_amount_candidate(candidates, seen_types, "supply_amount", supply_amount, source_block_id, confidence)
                _append_amount_candidate(candidates, seen_types, "vat_amount", vat_amount, source_block_id, confidence)
                _append_amount_candidate(candidates, seen_types, "final_amount", corrected_total, source_block_id, confidence)
                _append_amount_candidate(candidates, seen_types, "paid_amount", corrected_total, source_block_id, confidence)
                _append_amount_candidate(candidates, seen_types, "total_amount", corrected_total, source_block_id, confidence)
                return


def _split_tax_amount_options_near_total(lines: list[Mapping[str, Any]], total_index: int) -> set[int]:
    fragments: list[tuple[int, str]] = []
    for nearby_index in range(max(total_index - 14, 0), total_index):
        text = _safe_line_text(lines[nearby_index]) or ""
        fragment = _tax_summary_fragment_digits(text)
        if fragment is None:
            continue
        if not re.fullmatch(r"[1-9]\d{0,2}", fragment):
            continue
        fragments.append((nearby_index, fragment))

    amounts: set[int] = set()
    for left_offset, (left_index, left_fragment) in enumerate(fragments):
        for right_index, right_fragment in fragments[left_offset + 1 :]:
            if right_index - left_index > 4:
                continue
            if len(right_fragment) == 3:
                amounts.add(int(f"{left_fragment}{right_fragment}"))
            if len(left_fragment) == 3:
                amounts.add(int(f"{right_fragment}{left_fragment}"))
    return {amount for amount in amounts if 100 <= amount <= 1_000_000}


def _tax_summary_fragment_digits(text: str) -> str | None:
    stripped = re.sub(r"[\uc6d0\u20a9\s]", "", str(text or ""))
    return _amount_fragment_digits(stripped, allow_zero_group=False)


def _first_total_label_index(lines: list[Mapping[str, Any]]) -> int | None:
    for index, line in enumerate(lines[:30]):
        text = _safe_line_text(line)
        if not text:
            continue
        compact = _compact_line(text)
        if _has_any_label(compact, FINAL_LABELS) or _has_any_label(compact, TOTAL_LABELS):
            return index
    return None


def _standalone_amount_rows(lines: list[Mapping[str, Any]]) -> list[tuple[int, str, float | None]]:
    amount_rows: list[tuple[int, str, float | None]] = []
    for line in lines[:20]:
        text = _safe_line_text(line)
        if not text or not _is_standalone_amount_line(text):
            continue
        amount = _last_reasonable_amount(text)
        if amount is None or amount < 1000:
            continue
        index = _line_order_index(lines, line)
        if index is not None and _looks_like_pos_identifier_amount(lines, index, amount):
            continue
        amount_rows.append(
            (
                amount,
                str(line.get("block_id") or ""),
                _optional_float(line.get("confidence")),
            )
        )
    return amount_rows


def _has_card_evidence(lines: list[Mapping[str, Any]]) -> bool:
    for line in lines:
        text = _safe_line_text(line)
        if text and any(label in _compact_line(text) for label in PAYMENT_CARD_LABELS):
            return True
    return False


def _top_standalone_amount(lines: list[Mapping[str, Any]]) -> tuple[int, str, float | None, int] | None:
    first_card_index = _first_card_evidence_index(lines)
    amount_rows = _standalone_amount_rows_with_index(lines[:4])
    if first_card_index is not None:
        amount_rows = [row for row in amount_rows if row[3] < first_card_index]
    amount_rows = [
        row
        for row in amount_rows
        if row[0] <= 300_000 and (row[2] is None or row[2] >= 0.9)
    ]
    if not amount_rows:
        return None
    amount, source_block_id, confidence, index = sorted(amount_rows, key=lambda item: -item[0])[0]
    return amount, source_block_id, confidence, index


def _standalone_amount_rows_with_index(lines: list[Mapping[str, Any]]) -> list[tuple[int, str, float | None, int]]:
    amount_rows: list[tuple[int, str, float | None, int]] = []
    for index, line in enumerate(lines[:20]):
        text = _safe_line_text(line)
        if not text or not _is_standalone_amount_line(text):
            continue
        amount = _last_reasonable_amount(text)
        if amount is None or amount < 1000:
            continue
        if _looks_like_pos_identifier_amount(lines, index, amount):
            continue
        amount_rows.append(
            (
                amount,
                str(line.get("block_id") or ""),
                _optional_float(line.get("confidence")),
                index,
            )
        )
    return amount_rows


def _first_card_evidence_index(lines: list[Mapping[str, Any]]) -> int | None:
    for index, line in enumerate(lines):
        text = _safe_line_text(line)
        if text and any(label in _compact_line(text) for label in PAYMENT_CARD_LABELS):
            return index
    return None


def _has_split_card_marker(lines: list[Mapping[str, Any]], index: int) -> bool:
    nearby_compact = "".join(
        _compact_line(_safe_line_text(lines[nearby_index]) or "")
        for nearby_index in range(index, min(index + 5, len(lines)))
    )
    normalized = re.sub(r"[^0-9a-z가-힣]", "", nearby_compact)
    if "카드" not in normalized and "신용카" not in normalized:
        return False
    card_context = ("번호", "종류", "일시", "할부", "승인", "매입", "발급")
    return any(marker in normalized for marker in card_context)


def _line_order_index(lines: list[Mapping[str, Any]], target: Mapping[str, Any]) -> int | None:
    for index, line in enumerate(lines):
        if line is target:
            return index
    target_block_id = str(target.get("block_id") or "")
    if not target_block_id:
        return None
    for index, line in enumerate(lines):
        if str(line.get("block_id") or "") == target_block_id:
            return index
    return None


def _looks_like_pos_identifier_amount(lines: list[Mapping[str, Any]], index: int, amount: int) -> bool:
    if amount < 10_000 or amount > 999_999:
        return False
    text = _safe_line_text(lines[index]) or ""
    if "," in text or "." in text or " " in text:
        return False
    for nearby_index in range(max(index - 2, 0), min(index + 3, len(lines))):
        if nearby_index == index:
            continue
        nearby_text = _safe_line_text(lines[nearby_index]) or ""
        compact = _compact_line(nearby_text).upper()
        if "POS" in compact or re.search(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", nearby_text):
            return True
    return False


def _is_valid_date_candidate(value: str) -> bool:
    text = str(value or "").strip().split()[0]
    if not text:
        return False
    normalized = text.replace(".", "-").replace("/", "-")
    formats = ["%Y-%m-%d", "%y-%m-%d"]
    if re.fullmatch(r"\d{8}", normalized):
        formats = ["%Y%m%d"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(normalized, fmt)
        except ValueError:
            continue
        return 2000 <= parsed.year <= 2099
    return False


def _has_top_repeated_amount(lines: list[Mapping[str, Any]]) -> bool:
    repeated = _repeated_standalone_amount(lines)
    if repeated is None:
        return False
    _, source_block_id, _ = repeated
    for line in lines[:6]:
        if str(line.get("block_id") or "") == source_block_id:
            return True
    return False


def _has_strong_repeated_amount(lines: list[Mapping[str, Any]]) -> bool:
    repeated = _repeated_standalone_amount(lines, min_count=3)
    return repeated is not None


def _has_repeated_split_amount(lines: list[Mapping[str, Any]]) -> bool:
    grouped: dict[int, int] = {}
    for amount, _, _ in _split_standalone_amount_rows(lines):
        grouped[amount] = grouped.get(amount, 0) + 1
    return any(count >= 2 for count in grouped.values())


def _card_labeled_split_amount(lines: list[Mapping[str, Any]]) -> tuple[int, str, float | None] | None:
    for index in range(0, min(len(lines) - 1, 100)):
        current_text = _safe_line_text(lines[index])
        next_text = _safe_line_text(lines[index + 1])
        if not current_text or not next_text:
            continue
        first_fragment = _amount_fragment_digits(current_text)
        second_fragment = _loose_trailing_amount_fragment_digits(next_text)
        if first_fragment is None or second_fragment is None or len(first_fragment) > 2:
            continue
        nearby_compact = "".join(
            _compact_line(_safe_line_text(lines[nearby_index]) or "")
            for nearby_index in range(index, min(index + 7, len(lines)))
        )
        has_card_marker = "카드" in nearby_compact or "신용" in nearby_compact or "체크" in nearby_compact or "카" in nearby_compact
        has_tax_marker = "부가" in nearby_compact or "가세" in nearby_compact or "과세" in nearby_compact
        if not (has_card_marker and has_tax_marker):
            continue
        amount = int(f"{first_fragment}{second_fragment}")
        if 1_000 <= amount <= 1_000_000:
            return amount, str(lines[index].get("block_id") or ""), _optional_float(lines[index].get("confidence"))
    return None


def _repeated_standalone_amount(lines: list[Mapping[str, Any]], *, min_count: int = 2) -> tuple[int, str, float | None] | None:
    grouped: dict[int, list[tuple[str, float | None]]] = {}
    amount_rows = [*_standalone_amount_rows(lines), *_split_standalone_amount_rows(lines)]
    for amount, source_block_id, confidence in amount_rows:
        grouped.setdefault(amount, []).append((source_block_id, confidence))

    repeated = [
        (amount, amount_lines)
        for amount, amount_lines in grouped.items()
        if len(amount_lines) >= min_count
    ]
    if not repeated:
        return None
    amount, amount_lines = sorted(repeated, key=lambda item: (-item[0], -len(item[1])))[0]
    source_block_id, confidence = amount_lines[0]
    return amount, source_block_id, confidence


def _split_standalone_amount_rows(lines: list[Mapping[str, Any]]) -> list[tuple[int, str, float | None]]:
    amount_rows: list[tuple[int, str, float | None]] = []
    for index in range(0, min(len(lines) - 1, 120)):
        current_text = _safe_line_text(lines[index])
        next_text = _safe_line_text(lines[index + 1])
        if not current_text or not next_text:
            continue
        current_compact = _compact_line(current_text)
        next_compact = _compact_line(next_text)
        if _has_blocking_non_amount_label(current_compact) or _has_blocking_non_amount_label(next_compact):
            continue
        first_fragment = _amount_fragment_digits(current_text)
        second_fragment = _loose_trailing_amount_fragment_digits(next_text)
        if first_fragment is None or second_fragment is None:
            continue
        if len(first_fragment) > 2:
            continue
        amount = int(f"{first_fragment}{second_fragment}")
        if amount < 1_000 or amount > 1_000_000:
            continue
        amount_rows.append(
            (
                amount,
                str(lines[index].get("block_id") or ""),
                _optional_float(lines[index].get("confidence")),
            )
        )
    return amount_rows


def _safe_line_text(line: Mapping[str, Any]) -> str | None:
    if line.get("sensitive_category"):
        return None
    text = str(line.get("normalized_text") or line.get("text") or "").strip()
    if not text or text == "[REDACTED]":
        return None
    return text


def _compact_line_with_next(lines: list[Mapping[str, Any]], index: int) -> str:
    compact = _compact_line(_safe_line_text(lines[index]) or "")
    if compact not in {"부", "부가"}:
        return compact
    next_text = _safe_line_text(lines[index + 1]) if index + 1 < len(lines) else ""
    return _compact_line(f"{compact}{next_text or ''}")


def _joined_date_fragment(lines: list[Mapping[str, Any]], index: int) -> str | None:
    text = _safe_line_text(lines[index])
    if not text:
        return None
    next_text = _safe_line_text(lines[index + 1]) if index + 1 < len(lines) else None
    if not next_text:
        return None
    combined = re.sub(r"\s+", "", f"{text}{next_text}")
    combined = re.sub(r"[-./]{2,}", "-", combined)
    if DATE_CANDIDATE_PATTERN.search(combined):
        return combined
    return None


def _joined_korean_date_fragment(lines: list[Mapping[str, Any]], index: int) -> str | None:
    text = _safe_line_text(lines[index])
    if not text:
        return None
    year_month_match = re.search(r"(20\d{2})\s*\ub144\s*(\d{1,2})\s*[\uc6d4\uc6d0]", text)
    if year_month_match:
        same_line_day_match = re.search(r"[\uc6d4\uc6d0]\s*(\d{1,2})\s*\uc77c", text)
        if same_line_day_match:
            day = int(same_line_day_match.group(1))
            if 1 <= day <= 31:
                return f"{year_month_match.group(1)}-{int(year_month_match.group(2)):02d}-{day:02d}"
        for nearby_index in range(max(index - 4, 0), min(index + 5, len(lines))):
            if nearby_index == index:
                continue
            nearby_text = _safe_line_text(lines[nearby_index]) or ""
            day_match = re.search(r"\b(\d{1,2})\s*\uc77c", nearby_text)
            if not day_match:
                continue
            day = int(day_match.group(1))
            if 1 <= day <= 31:
                return f"{year_month_match.group(1)}-{int(year_month_match.group(2)):02d}-{day:02d}"
    year_match = re.search(r"(20\d{2})", text)
    if not year_match:
        return None
    year = year_match.group(1)
    month: str | None = None
    day: str | None = None
    for nearby_index in range(index + 1, min(index + 8, len(lines))):
        candidate_text = _safe_line_text(lines[nearby_index])
        if not candidate_text:
            continue
        compact = _compact_line(candidate_text)
        if "pos" in compact or "tel" in compact or "전화" in compact:
            continue
        month_match = re.search(r"년\s*(\d{1,2})", candidate_text)
        if month_match:
            month = month_match.group(1)
        day_match = re.search(r"월\s*(\d{1,2})", candidate_text)
        if day_match:
            day = day_match.group(1)
        if month and day:
            return f"{year}-{int(month):02d}-{int(day):02d}"
    return None


def _labeled_flexible_short_date_fragment(lines: list[Mapping[str, Any]], index: int) -> str | None:
    text = _safe_line_text(lines[index])
    if not text:
        return None
    nearby_text = " ".join(
        _safe_line_text(lines[nearby_index]) or ""
        for nearby_index in range(max(index - 2, 0), min(index + 4, len(lines)))
    )
    nearby_compact = _compact_line(nearby_text)
    if not _has_any_label(nearby_compact, KOREAN_DATE_LABELS):
        return None
    if any(token in nearby_compact for token in ("\uc2b9\uc778\ubc88\ud638", "\uce74\ub4dc\ubc88\ud638", "\uace0\uc720\ubc88\ud638")):
        if not any(label in nearby_compact for label in ("\uc2b9\uc778\uc77c", "\uc2b9\uc778\uc77c\uc2dc", "\uac70\ub798\uc77c\uc2dc")):
            return None
    for nearby_index in range(index, min(index + 4, len(lines))):
        candidate_text = _safe_line_text(lines[nearby_index])
        if not candidate_text:
            continue
        digits = re.sub(r"\D", "", candidate_text)
        if len(digits) >= 8 and digits[:2] in {"19", "20"} and _has_nearby_time_fragment(lines, nearby_index):
            continue
        candidate = _flexible_date_candidate_from_text(candidate_text)
        if candidate:
            return candidate
    return None


def _flexible_date_candidate_from_text(text: str) -> str | None:
    value = str(text or "").strip()
    if not value:
        return None
    separated_match = re.search(r"\b((?:19|20)\d{2})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})\b", value)
    if separated_match:
        candidate = f"{int(separated_match.group(1)):04d}-{int(separated_match.group(2)):02d}-{int(separated_match.group(3)):02d}"
        return candidate if _is_valid_date_candidate(candidate) else None
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 8 and digits[:2] in {"19", "20"}:
        candidate = f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        return candidate if _is_valid_date_candidate(candidate) else None
    if len(digits) == 6 and digits.startswith("20"):
        year = int(digits[:4])
        month = int(digits[4])
        day = int(digits[5])
        candidate = f"{year:04d}-{month:02d}-{day:02d}"
        return candidate if _is_valid_date_candidate(candidate) else None
    return None


def _has_nearby_time_fragment(lines: list[Mapping[str, Any]], index: int) -> bool:
    for nearby_index in range(index + 1, min(index + 3, len(lines))):
        text = _safe_line_text(lines[nearby_index]) or ""
        if re.search(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", text):
            return True
    return False


def _labeled_short_date_fragment(lines: list[Mapping[str, Any]], index: int) -> str | None:
    text = _safe_line_text(lines[index])
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) < 6:
        return None
    if re.search(r"\b\d{2,4}[-./]\d{1,2}[-./]\d{1,2}", text):
        return None
    nearby_text = " ".join(
        _safe_line_text(lines[nearby_index]) or ""
        for nearby_index in range(max(index - 1, 0), min(index + 2, len(lines)))
    )
    nearby_compact = _compact_line(nearby_text)
    date_labels = (
        "승인일시",
        "발행일시",
        "거래일시",
        "거래일자",
        "매출일",
        "매출일자",
        "판매일",
        "판매일자",
        "판매시간",
        "인쇄일자",
        "등록",
    )
    if not any(label in nearby_compact for label in date_labels):
        return None
    if len(digits) >= 8 and digits[:2] in {"19", "20"}:
        year = int(digits[:4])
        month = int(digits[4:6])
        day = int(digits[6:8])
    else:
        year = 2000 + int(digits[:2])
        month = int(digits[2:4])
        day = int(digits[4:6])
    if not (2000 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31):
        return None
    candidate = f"{year}-{month:02d}-{day:02d}"
    if not _is_valid_date_candidate(candidate):
        return None
    return candidate


def _labeled_compact_datetime_fragment(lines: list[Mapping[str, Any]], index: int) -> str | None:
    text = _safe_line_text(lines[index])
    if not text:
        return None
    nearby_text = " ".join(
        _safe_line_text(lines[nearby_index]) or ""
        for nearby_index in range(max(index - 2, 0), min(index + 3, len(lines)))
    )
    nearby_compact = _compact_line(nearby_text)
    datetime_labels = (
        "승인일시",
        "승인시간",
        "거래일시",
        "거래일자",
        "매출일",
        "매출일자",
        "판매시간",
    )
    if not any(label in nearby_compact for label in datetime_labels):
        return None
    if any(token in nearby_compact for token in ("승인번호", "카드번호", "고유번호")) and not any(
        label in nearby_compact for label in ("승인일시", "승인시간", "거래일시", "거래일자")
    ):
        return None
    joined_text = " ".join(
        _safe_line_text(lines[nearby_index]) or ""
        for nearby_index in range(index, min(index + 3, len(lines)))
    )
    match = re.search(r"\b((?:19|20)\d{6})\s+(\d{1,2}:\d{2}(?::\d{2})?)\b", joined_text)
    if not match:
        match = re.search(r"\b((?:19|20)\d{6})(\d{2})(\d{2})(\d{2})\b", joined_text)
        if not match:
            return None
        hour = int(match.group(2))
        minute = int(match.group(3))
        second = int(match.group(4))
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            return None
        candidate = f"{match.group(1)} {hour:02d}:{minute:02d}:{second:02d}"
        if not _is_valid_date_candidate(candidate):
            return None
        return candidate
    candidate = f"{match.group(1)} {match.group(2)}"
    if not _is_valid_date_candidate(candidate):
        return None
    return candidate


def _noisy_embedded_compact_datetime_fragment(lines: list[Mapping[str, Any]], index: int) -> str | None:
    text = _safe_line_text(lines[index])
    if not text:
        return None
    nearby_text = " ".join(
        _safe_line_text(lines[nearby_index]) or ""
        for nearby_index in range(max(index - 8, 0), min(index + 9, len(lines)))
    )
    nearby_compact = _compact_line(nearby_text)
    has_datetime_context = any(
        label in nearby_compact
        for label in ("승인일시", "승인시간", "거래일시", "거래일자", "매출일", "매출일자")
    ) or ("승" in nearby_compact and "인" in nearby_compact and ("시" in nearby_compact or "간" in nearby_compact))
    if not has_datetime_context:
        return None
    if any(token in nearby_compact for token in ("승인번호", "카드번호", "고유번호")) and not any(
        label in nearby_compact for label in ("승인일시", "승인시간", "거래일시", "거래일자")
    ):
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) < 12:
        return None
    for start in range(0, max(len(digits) - 14 + 1, 0)):
        candidate = _compact_datetime_candidate_from_digits(digits[start : start + 14], full_year=True)
        if candidate:
            return candidate
    for start in range(0, max(len(digits) - 12 + 1, 0)):
        candidate = _compact_datetime_candidate_from_digits(digits[start : start + 12], full_year=False)
        if candidate:
            return candidate
    return None


def _compact_datetime_candidate_from_digits(digits: str, *, full_year: bool) -> str | None:
    if full_year:
        if not re.fullmatch(r"(?:19|20)\d{12}", digits):
            return None
        year = int(digits[:4])
        month = int(digits[4:6])
        day = int(digits[6:8])
        hour = int(digits[8:10])
        minute = int(digits[10:12])
        second = int(digits[12:14])
        date_part = digits[:8]
    else:
        if not re.fullmatch(r"\d{12}", digits):
            return None
        short_year = int(digits[:2])
        if short_year < 20 or short_year > 39:
            return None
        year = 2000 + short_year
        month = int(digits[2:4])
        day = int(digits[4:6])
        hour = int(digits[6:8])
        minute = int(digits[8:10])
        second = int(digits[10:12])
        date_part = f"{year:04d}{month:02d}{day:02d}"
    if not (2000 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31):
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        return None
    candidate = f"{date_part} {hour:02d}:{minute:02d}:{second:02d}"
    if not _is_valid_date_candidate(candidate):
        return None
    return candidate


def _labeled_approval_number_value(lines: list[Mapping[str, Any]], index: int) -> str | None:
    text = _safe_line_text(lines[index])
    if not text:
        return None
    compact = _compact_line(text).upper()
    if not any(_compact_line(label).upper() in compact for label in APPROVAL_NUMBER_LABELS):
        return None

    same_line = _approval_number_candidate_after_label(text)
    if same_line:
        return same_line

    for nearby_index in range(index + 1, min(index + 4, len(lines))):
        candidate_text = _safe_line_text(lines[nearby_index])
        if not candidate_text:
            continue
        candidate_compact = _compact_line(candidate_text).upper()
        if any(_compact_line(label).upper() in candidate_compact for label in APPROVAL_NUMBER_LABELS):
            continue
        if _has_blocking_non_approval_number_label(candidate_compact):
            return None
        candidate = _approval_number_candidate_from_text(candidate_text)
        if candidate:
            return candidate
    return None


def _approval_number_candidate_after_label(text: str) -> str | None:
    match = re.search(
        r"(?:승인\s*(?:번호|NO|No|no)|approval\s*(?:no|number)|approval_no)\s*[:：#\-]?\s*(.+?)\s*$",
        str(text or ""),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return _approval_number_candidate_from_text(match.group(1))


def _approval_number_candidate_from_text(text: str) -> str | None:
    value = str(text or "").strip()
    if not value or value == "[REDACTED]":
        return None
    if BUSINESS_NUMBER_CANDIDATE_PATTERN.search(value) or PHONE_LIKE_PATTERN.search(value) or CARD_LIKE_PATTERN.search(value):
        return None
    compact = _compact_line(value)
    if any(token in compact for token in ("카드번호", "사업자", "전화", "TEL", "합계", "총금액", "공급", "부가", "세액")):
        return None
    digits = re.sub(r"\D", "", value)
    if not (6 <= len(digits) <= 15):
        return None
    if set(digits) == {"0"}:
        return None
    return digits


def _has_blocking_non_approval_number_label(compact: str) -> bool:
    blocking_labels = (
        "승인일시",
        "승인시간",
        "거래일시",
        "거래일자",
        "매출일",
        "매출일자",
        "카드번호",
        "사업자",
        "대표",
        "주소",
        "TEL",
        "전화",
        "합계",
        "총금액",
        "공급",
        "부가",
        "세액",
    )
    return any(label in compact for label in blocking_labels)


def _joined_business_number_fragment(lines: list[Mapping[str, Any]], index: int) -> str | None:
    top_split = _top_split_business_number_fragment(lines, index)
    if top_split is not None:
        return top_split
    nearby_text = " ".join(
        _safe_line_text(lines[nearby_index]) or ""
        for nearby_index in range(max(index - 2, 0), min(index + 3, len(lines)))
    )
    if "*" in nearby_text:
        return None
    nearby_compact = _compact_line(nearby_text).upper()
    text = _safe_line_text(lines[index]) or ""
    bracket_fragment = "[" in text or "]" in nearby_text
    if not (
        "사업자" in nearby_compact
        or "자번호" in nearby_compact
        or "사업자등록" in nearby_compact
        or "고유번호" in nearby_compact
        or "NO" in nearby_compact
        or "N0" in nearby_compact
        or bracket_fragment
    ):
        return None
    if any(token in nearby_compact for token in ("카드", "승인", "일시불", "POS")):
        return None
    fragments: list[str] = []
    for nearby_index in range(index, min(index + 3, len(lines))):
        text = _safe_line_text(lines[nearby_index])
        if not text:
            break
        compact = _compact_line(text)
        if _has_blocking_non_amount_label(compact) and nearby_index != index:
            return None
        fragment = re.sub(r"\D", "", text)
        if not fragment:
            if fragments:
                break
            return None
        fragments.append(fragment)
        if len("".join(fragments)) >= 10:
            break
    digits = "".join(fragments)
    if len(fragments) < 2:
        return None
    if len(digits) != 10:
        return None
    return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"


def _reverse_labeled_business_number_fragment(lines: list[Mapping[str, Any]], index: int) -> str | None:
    text = _safe_line_text(lines[index]) or ""
    compact = _compact_line(text)
    if "\uc0ac\uc5c5\uc790" not in compact and "N0" not in compact.upper() and "NO" not in compact.upper():
        return None
    current_digits = re.sub(r"\D", "", text)
    if len(current_digits) > 5:
        current_digits = current_digits[-5:]
    if len(current_digits) != 5:
        return None
    for nearby_index in range(index - 1, max(index - 4, -1), -1):
        previous_text = _safe_line_text(lines[nearby_index]) or ""
        if "*" in previous_text:
            continue
        previous_digits = re.sub(r"\D", "", previous_text)
        if len(previous_digits) != 5:
            continue
        digits = f"{current_digits}{previous_digits}"
        candidate = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        if _has_valid_business_number_checksum(candidate):
            return candidate
    return None


def _top_split_business_number_fragment(lines: list[Mapping[str, Any]], index: int) -> str | None:
    if index > 8 or index + 1 >= len(lines):
        return None
    text = _safe_line_text(lines[index]) or ""
    next_text = _safe_line_text(lines[index + 1]) or ""
    if "-" not in text:
        return None
    nearby_text = " ".join(
        _safe_line_text(lines[nearby_index]) or ""
        for nearby_index in range(max(index - 4, 0), min(index + 5, len(lines)))
    )
    nearby_compact = _compact_line(nearby_text).upper()
    if any(token in nearby_compact for token in ("카드번호", "승인번호", "일시불", "POS")):
        return None
    digits = re.sub(r"\D", "", f"{text}{next_text}")
    if len(digits) != 10:
        return None
    candidate = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    if not _has_valid_business_number_checksum(candidate):
        return None
    return candidate


def _looks_like_card_business_number_false_positive(
    lines: list[Mapping[str, Any]], index: int, business_text: str
) -> bool:
    if "*" in str(business_text or ""):
        return True
    if "-" in str(business_text or "") and BUSINESS_NUMBER_CANDIDATE_PATTERN.search(str(business_text or "")):
        return False
    nearby_text = " ".join(
        _safe_line_text(lines[nearby_index]) or ""
        for nearby_index in range(max(index - 8, 0), min(index + 9, len(lines)))
    )
    nearby_compact = _compact_line(nearby_text).upper()
    has_business_evidence = any(
        token in nearby_compact
        for token in ("사업자", "자번호", "사업자등록", "고유번호", "NO", "N0")
    ) or "[" in nearby_text or "]" in nearby_text
    try:
        line_order = int(lines[index].get("line_order") or index)
    except (TypeError, ValueError):
        line_order = index
    if not has_business_evidence and (index > 30 or line_order > 30):
        return True
    if not has_business_evidence and any(
        token in nearby_compact for token in ("카드번호", "카드종류", "카드명", "일시불", "승인번호", "POS")
    ):
        return True
    return False


def _has_valid_business_number_checksum(value: str) -> bool:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 10:
        return False
    numbers = [int(char) for char in digits]
    weights = [1, 3, 7, 1, 3, 7, 1, 3]
    checksum_sum = sum(numbers[index] * weights[index] for index in range(8))
    ninth_product = numbers[8] * 5
    checksum_sum += ninth_product // 10 + ninth_product % 10
    return (10 - (checksum_sum % 10)) % 10 == numbers[9]


def _labeled_business_number_prefix_fragment(lines: list[Mapping[str, Any]], index: int) -> str | None:
    text = _safe_line_text(lines[index])
    if not text:
        return None
    if BUSINESS_NUMBER_CANDIDATE_PATTERN.search(text):
        return None
    compact = _compact_line(text).upper()
    if not (
        "사업자" in compact
        or "고유번호" in compact
        or "NO" in compact
        or "N0" in compact
    ):
        return None
    normalized = str(text).translate(str.maketrans({"O": "0", "o": "0"}))
    prefix_match = re.search(r"(\d{3})[-\s]?(\d{2})[-\s]*$", normalized)
    if not prefix_match:
        return None
    prefix = "".join(prefix_match.groups())
    for nearby_index in range(index + 1, min(index + 9, len(lines))):
        candidate_text = _safe_line_text(lines[nearby_index])
        if not candidate_text:
            continue
        if PHONE_LIKE_PATTERN.search(candidate_text):
            continue
        candidate_compact = _compact_line(candidate_text)
        if DATE_CANDIDATE_PATTERN.search(candidate_text):
            break
        if _has_blocking_non_amount_label(candidate_compact):
            continue
        suffix = re.sub(r"\D", "", candidate_text)
        if len(suffix) == 5:
            return f"{prefix[:3]}-{prefix[3:5]}-{suffix}"
    return None


def _labeled_merchant_value(text: str) -> str | None:
    for label in sorted(MERCHANT_LABELS, key=len, reverse=True):
        flexible_label = r"\s*".join(re.escape(char) for char in label)
        match = re.match(rf"\s*{flexible_label}\s*[:\-\u2013\u2014]?\s*(.+?)\s*$", text)
        if not match:
            continue
        value = str(match.group(1) or "").strip()
        if not value or value == "[REDACTED]":
            return None
        value = _strip_leading_store_number(value)
        if len(value) > 80:
            return None
        if DATE_CANDIDATE_PATTERN.search(value) or BUSINESS_NUMBER_CANDIDATE_PATTERN.search(value):
            return None
        if PHONE_LIKE_PATTERN.search(value) or CARD_LIKE_PATTERN.search(value):
            return None
        if _last_reasonable_amount(value) is not None:
            return None
        if _is_labeled_merchant_noise_value(value):
            return None
        if not _looks_like_labeled_merchant_value(value):
            return None
        return find_merchant_by_name_fragment(value) or value
    return None


def _strip_leading_store_number(value: str) -> str:
    match = re.match(r"^\s*\d{1,4}\s*[\).,:\-]?\s+(.+?)\s*$", str(value or ""))
    if not match:
        return str(value or "").strip()
    candidate = str(match.group(1) or "").strip()
    if re.search(r"[가-힣A-Za-z]", candidate):
        return candidate
    return str(value or "").strip()


def _next_labeled_merchant_value(lines: list[Mapping[str, Any]], index: int) -> str | None:
    text = _safe_line_text(lines[index])
    if not text:
        return None
    compact = _compact_line(text)
    if not any(label in compact for label in MERCHANT_LABELS):
        return None
    for nearby_index in range(index + 1, min(index + 6, len(lines))):
        candidate = _safe_line_text(lines[nearby_index])
        if not candidate:
            continue
        candidate_compact = _compact_line(candidate)
        if candidate_compact in {"-", "－", "−", "–", "—"}:
            continue
        if any(label in candidate_compact for label in MERCHANT_LABELS):
            continue
        if (
            DATE_CANDIDATE_PATTERN.search(candidate)
            or BUSINESS_NUMBER_CANDIDATE_PATTERN.search(candidate)
            or PHONE_LIKE_PATTERN.search(candidate)
            or CARD_LIKE_PATTERN.search(candidate)
            or _last_reasonable_amount(candidate) is not None
        ):
            continue
        if _has_blocking_non_amount_label(candidate_compact):
            continue
        if _is_labeled_merchant_noise_value(candidate):
            continue
        if _is_nearby_owner_name_candidate(lines, nearby_index):
            continue
        if _looks_like_labeled_merchant_value(candidate):
            return find_merchant_by_name_fragment(candidate) or candidate
    return None


def _is_labeled_merchant_noise_value(text: str) -> bool:
    compact = _compact_line(text)
    noise_values = {
        "실제와",
        "주소가",
        "가맹점주소가",
        "다른",
        "경우",
        "신고안내",
        "포상금",
        "지급",
        "여신금융협회",
        "고객용",
        "영수증",
    }
    if compact in noise_values:
        return True
    return any(token in compact for token in ("신고안내", "포상금", "여신금융협회"))


def _is_nearby_owner_name_candidate(lines: list[Mapping[str, Any]], index: int) -> bool:
    text = _safe_line_text(lines[index]) or ""
    compact = _compact_line(text)
    if not re.fullmatch(r"[가-힣]{2,4}", compact):
        return False
    nearby_compact = _compact_line(
        " ".join(_safe_line_text(lines[nearby_index]) or "" for nearby_index in range(index + 1, min(index + 4, len(lines))))
    )
    return any(marker in nearby_compact for marker in ("대표", "대표자", "성명", "주인"))


def _business_block_merchant_value(lines: list[Mapping[str, Any]], index: int) -> str | None:
    text = _safe_line_text(lines[index])
    if not text:
        return None
    compact = _compact_line(text)
    if not (
        BUSINESS_NUMBER_CANDIDATE_PATTERN.search(text)
        or "사업자" in compact
        or "사업자등록" in compact
    ):
        return None
    merchant_from_same_line = _merchant_value_before_business_number(text)
    if merchant_from_same_line:
        return merchant_from_same_line
    merchant_from_business_number = find_merchant_by_business_number(text)
    if merchant_from_business_number and ("사업자" in compact or "사업자등록" in compact):
        return merchant_from_business_number
    for previous_index in range(index - 1, max(index - 8, -1), -1):
        candidate_line = lines[previous_index]
        if _is_business_block_merchant_candidate(candidate_line):
            candidate = _safe_line_text(candidate_line)
            return find_merchant_by_name_fragment(candidate) or candidate
    return None


def _app_screen_merchant_value(lines: list[Mapping[str, Any]], index: int) -> str | None:
    text = _safe_line_text(lines[index])
    if not text:
        return None
    candidate = _strip_leading_store_number(text)
    compact = _compact_line(candidate)
    if not _looks_like_app_screen_merchant(candidate):
        return None
    if any(token in compact for token in APP_SCREEN_MERCHANT_BLOCKERS):
        return None
    if _has_any_label(compact, KOREAN_DATE_LABELS) or _has_simple_total_amount_label(compact):
        return None
    previous_compact = _compact_line(
        " ".join(_safe_line_text(lines[nearby_index]) or "" for nearby_index in range(max(index - 8, 0), index))
    )
    next_compact = _compact_line(
        " ".join(_safe_line_text(lines[nearby_index]) or "" for nearby_index in range(index + 1, min(index + 8, len(lines))))
    )
    if sum(1 for marker in APP_SCREEN_MARKERS if marker in previous_compact) < 2:
        return None
    if not (
        _has_any_label(next_compact, KOREAN_DATE_LABELS)
        or _has_simple_total_amount_label(next_compact)
        or "\uce74\ub4dc\uc774\ub984" in next_compact
    ):
        return None
    return find_merchant_by_name_fragment(candidate) or candidate


def _is_app_navigation_label(lines: list[Mapping[str, Any]], index: int) -> bool:
    text = _safe_line_text(lines[index])
    if not text:
        return False
    compact = _compact_line(text).strip(":")
    if compact not in {"\uacb0\uc81c", "\ucde8\uc18c", "\uc815\ubcf4", "\uc601\uc218\uc99d"}:
        return False
    nearby_compact = _compact_line(
        " ".join(_safe_line_text(lines[nearby_index]) or "" for nearby_index in range(max(index - 3, 0), min(index + 5, len(lines))))
    )
    return any(marker in nearby_compact for marker in APP_SCREEN_MARKERS)


def _looks_like_app_screen_merchant(text: str) -> bool:
    value = str(text or "").strip()
    if len(value) < 2 or len(value) > 30 or value == "[REDACTED]":
        return False
    if DATE_CANDIDATE_PATTERN.search(value) or BUSINESS_NUMBER_CANDIDATE_PATTERN.search(value):
        return False
    if PHONE_LIKE_PATTERN.search(value) or CARD_LIKE_PATTERN.search(value):
        return False
    if _last_reasonable_amount(value) is not None:
        return False
    if re.search(r"\d{4,}", value):
        return False
    if _looks_like_address_fragment(_compact_line(value)):
        return False
    return bool(re.search(r"[\uac00-\ud7a3A-Za-z]", value))


def _merchant_value_before_business_number(text: str) -> str | None:
    match = BUSINESS_NUMBER_CANDIDATE_PATTERN.search(text)
    if not match:
        return None
    prefix = str(text[: match.start()] or "").strip()
    if not prefix:
        return None
    parts = [
        _clean_inline_merchant_segment(part)
        for part in re.split(r"[/|｜\\()\[\]{}:：]+", prefix)
    ]
    for candidate in reversed([part for part in parts if part]):
        if _is_inline_business_number_merchant_candidate(candidate):
            return candidate
    fallback = _clean_inline_merchant_segment(prefix)
    if _is_inline_business_number_merchant_candidate(fallback):
        return fallback
    return None


def _clean_inline_merchant_segment(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(
        r"^\s*(?:상호명?|매장명|가맹점명|점포명|사업장명|상점명)\s*[-:：]?\s*",
        "",
        text,
    )
    text = re.sub(r"^\s*\d{1,4}\s*[\).,:\-]?\s+", "", text)
    return text.strip(" \t\r\n-–—_.,;·")


def _is_inline_business_number_merchant_candidate(text: str) -> bool:
    value = str(text or "").strip()
    if len(value) < 2 or len(value) > 40 or value == "[REDACTED]":
        return False
    compact = _compact_line(value)
    if DATE_CANDIDATE_PATTERN.search(value) or BUSINESS_NUMBER_CANDIDATE_PATTERN.search(value):
        return False
    if PHONE_LIKE_PATTERN.search(value) or CARD_LIKE_PATTERN.search(value):
        return False
    if _last_reasonable_amount(value) is not None:
        return False
    if re.search(r"\d{6,}", value):
        return False
    blocked_tokens = (
        "사업자",
        "대표",
        "주소",
        "TEL",
        "전화",
        "승인",
        "카드",
        "합계",
        "공급",
        "부가",
        "세액",
        "번호",
        "고유",
        "고객용",
        "영수증",
        "수량",
    )
    if any(token.lower() in compact.lower() for token in blocked_tokens):
        return False
    if _looks_like_address_fragment(compact):
        return False
    return _looks_like_business_block_merchant(value)


def _top_known_merchant_value(lines: list[Mapping[str, Any]], index: int) -> str | None:
    if index > 5:
        return None
    line = lines[index]
    text = _safe_line_text(line)
    if not text:
        return None
    known_merchant = find_merchant_by_name_fragment(text)
    if known_merchant:
        return known_merchant
    compact = _compact_line(text)
    if "gste" in compact:
        return "GS THE FRESH"
    if "\uc0bc\uc131\uc804\uc790\uc11c\ube44\uc2a4" in compact:
        return "\uc0bc\uc131\uc804\uc790\uc11c\ube44\uc2a4"
    if "baskin" in compact or "robbins" in compact or "\ubc30\uc2a4\ud0a8\ub77c\ube48\uc2a4" in compact:
        return "\ubc30\uc2a4\ud0a8\ub77c\ube48\uc2a4"
    if not any(marker in compact for marker in TOP_MERCHANT_SUFFIX_MARKERS):
        return None
    if not _is_business_block_merchant_candidate(line):
        return None
    return text


def _is_business_block_merchant_candidate(line: Mapping[str, Any]) -> bool:
    value = _safe_line_text(line)
    text = str(value or "").strip()
    if not text or text == "[REDACTED]":
        return False
    confidence = _optional_float(line.get("confidence"))
    if confidence is not None and confidence < 0.85:
        return False
    if len(text) > 80:
        return False
    compact = _compact_line(text)
    if DATE_CANDIDATE_PATTERN.search(text) or BUSINESS_NUMBER_CANDIDATE_PATTERN.search(text):
        return False
    if PHONE_LIKE_PATTERN.search(text) or CARD_LIKE_PATTERN.search(text):
        return False
    if _last_reasonable_amount(text) is not None:
        return False
    if not _looks_like_business_block_merchant(text):
        return False
    blocked_tokens = (
        "영수증",
        "카드판매",
        "카드매출",
        "판매시간",
        "사업자",
        "사업",
        "자번호",
        "고유번호",
        "대표자",
        "주소",
        "테이블",
        "상품",
        "카드",
        "신용카드",
        "체크카드",
        "비씨카드",
        "승인",
        "일시불",
        "합계",
        "총금액",
        "공급",
        "부가",
        "세액",
    )
    if any(token in compact for token in blocked_tokens):
        return False
    return bool(re.search(r"[가-힣A-Za-z]", text))


def _looks_like_labeled_merchant_value(text: str) -> bool:
    value = str(text or "").strip()
    if len(value) < 2:
        return False
    compact = _compact_line(value)
    if compact in {"사업", "자번호", "사업자", "사업자번호", "전화", "전화번", "대표자"}:
        return False
    if re.fullmatch(r"[\d\s:._-]+", value):
        return False
    return bool(re.search(r"[가-힣A-Za-z]", value))


def _looks_like_business_block_merchant(text: str) -> bool:
    value = str(text or "").strip()
    if len(value) < 3:
        return False
    if re.fullmatch(r"[\d\s:._/-]+", value):
        return False
    compact = _compact_line(value)
    noise_tokens = (
        "영수증",
        "고객용",
        "판매",
        "시간",
        "승인",
        "번호",
        "주소",
        "대표",
        "확하고",
    )
    if any(token in compact for token in noise_tokens):
        return False
    if _looks_like_address_fragment(compact):
        return False
    business_markers = (
        "주식회사",
        "(주)",
        "㈜",
        "유한회사",
        "법인",
        "점",
        "지점",
        "본점",
        "점포",
        "마트",
        "카페",
        "커피",
        "식당",
        "고깃집",
        "축산",
        "유통",
        "김밥",
        "분식",
        "약국",
        "병원",
        "주유소",
        "상회",
        "상사",
        "식품",
        "호텔",
        "리조트",
        "비엠",
        "fresh",
    )
    return any(marker in compact for marker in business_markers)


def _looks_like_address_fragment(compact: str) -> bool:
    province_markers = (
        "서울특별시",
        "부산광역시",
        "대구광역시",
        "인천광역시",
        "광주광역시",
        "대전광역시",
        "울산광역시",
        "세종특별자치시",
        "경기도",
        "강원도",
        "충청북도",
        "충청남도",
        "전라북도",
        "전라남도",
        "경상북도",
        "경상남도",
        "제주특별자치도",
    )
    if any(marker in compact for marker in province_markers):
        return True
    if re.fullmatch(r"[가-힣]{2,8}(?:시|군|구|동|읍|면|로|길)", compact):
        return True
    return bool(re.search(r"(?:시|군|구)(?:[가-힣]{0,8})?(?:로|길|동|읍|면)$", compact))


def _has_zero_safe_amount_label(compact: str) -> bool:
    if _is_standalone_total_label(compact):
        return True
    label_groups = (
        SUPPLY_LABELS,
        VAT_LABELS,
        DISCOUNT_LABELS,
        GROSS_LABELS,
        PAID_AMOUNT_LABELS,
        FINAL_LABELS,
        SIMPLE_TOTAL_AMOUNT_LABELS,
    )
    return any(_has_any_label(compact, labels) for labels in label_groups)


def _has_simple_total_amount_label(compact: str) -> bool:
    return _has_any_label(compact, SIMPLE_TOTAL_AMOUNT_LABELS)


def _has_paid_amount_label(compact: str) -> bool:
    return _has_any_label(compact, PAID_AMOUNT_LABELS)


def _has_inline_card_amount_label(compact: str) -> bool:
    return _has_any_label(compact, PAYMENT_CARD_LABELS)


def _is_standalone_total_label(compact: str) -> bool:
    return compact.strip(":：") in {"계", "합계"}


def _next_nonempty_has_label(lines: list[Mapping[str, Any]], index: int, labels: tuple[str, ...]) -> bool:
    for nearby_index in range(index + 1, min(index + 4, len(lines))):
        text = _safe_line_text(lines[nearby_index])
        if not text:
            continue
        compact = _compact_line(text)
        if compact in {"-", "－", "−", "–", "—"}:
            continue
        return _has_any_label(compact, labels)
    return False


def _nearby_labeled_amount(
    lines: list[Mapping[str, Any]],
    index: int,
    *,
    allow_zero: bool = False,
    max_lines: int = 2,
    prefer_largest: bool = False,
) -> int | None:
    amounts: list[int] = []
    for nearby_index in range(index + 1, min(index + max_lines + 1, len(lines))):
        candidate_text = _safe_line_text(lines[nearby_index])
        if not candidate_text:
            continue
        candidate_compact = _compact_line(candidate_text)
        if _has_blocking_non_amount_label(candidate_compact):
            return None
        if not _is_standalone_amount_line(candidate_text):
            continue
        amount = _last_reasonable_amount(candidate_text, allow_zero=allow_zero)
        if amount is None:
            continue
        if _looks_like_pos_identifier_amount(lines, nearby_index, amount):
            continue
        if amount == 0 and allow_zero:
            if prefer_largest:
                continue
            return amount
        if amount < 1000:
            continue
        if not prefer_largest:
            return amount
        amounts.append(amount)
    return max(amounts) if amounts else None


def _nearby_split_amount_fragments(lines: list[Mapping[str, Any]], index: int, *, max_lines: int = 4) -> int | None:
    fragments: list[str] = []
    for nearby_index in range(index + 1, min(index + max_lines + 1, len(lines))):
        candidate_text = _safe_line_text(lines[nearby_index])
        if not candidate_text:
            continue
        candidate_compact = _compact_line(candidate_text)
        if _has_blocking_non_amount_label(candidate_compact):
            return None
        if candidate_compact in {"-", "－", "−", "–", "—"}:
            continue
        fragment = _amount_fragment_digits(candidate_text, allow_zero_group=True)
        if fragment is None:
            if fragments:
                break
            continue
        fragments.append(fragment)
        if len(fragments) >= 2:
            amount_text = "".join(fragments[:2])
            if len(fragments[0]) <= 2 and all(len(part) == 3 for part in fragments[1:2]):
                amount = int(amount_text)
                if 1_000 <= amount <= 10_000_000:
                    return amount
    return None


def _nearby_currency_split_amount(lines: list[Mapping[str, Any]], index: int, *, max_lines: int = 3) -> int | None:
    first_fragment: str | None = None
    for nearby_index in range(index + 1, min(index + max_lines + 1, len(lines))):
        candidate_text = _safe_line_text(lines[nearby_index])
        if not candidate_text:
            continue
        candidate_compact = _compact_line(candidate_text)
        if candidate_compact == "-":
            continue
        if _has_blocking_non_amount_label(candidate_compact):
            return None
        if first_fragment is None:
            first_fragment = _leading_currency_amount_fragment(candidate_text)
            continue
        second_fragment = _trailing_currency_amount_fragment(candidate_text)
        if second_fragment is None:
            return None
        amount = int(f"{first_fragment}{second_fragment}")
        if 1_000 <= amount <= 10_000_000:
            return amount
        return None
    return None


def _split_amount_around_label(lines: list[Mapping[str, Any]], index: int) -> int | None:
    previous_fragment: str | None = None
    next_fragment: str | None = None
    for nearby_index in range(index - 1, max(index - 4, -1), -1):
        text = _safe_line_text(lines[nearby_index])
        if not text:
            continue
        compact = _compact_line(text)
        if _has_blocking_non_amount_label(compact):
            break
        fragment = _amount_fragment_digits(text, allow_zero_group=False)
        if fragment is None:
            continue
        if re.fullmatch(r"[1-9]\d{0,2}", fragment):
            previous_fragment = fragment
            break
        break
    if previous_fragment is None:
        return None
    for nearby_index in range(index + 1, min(index + 4, len(lines))):
        text = _safe_line_text(lines[nearby_index])
        if not text:
            continue
        if "-" in text:
            break
        compact = _compact_line(text)
        if _has_blocking_non_amount_label(compact):
            break
        fragment = _amount_fragment_digits(text, allow_zero_group=True)
        if fragment is None:
            continue
        if re.fullmatch(r"\d{3}", fragment):
            next_fragment = fragment
            break
        break
    if next_fragment is None:
        return None
    amount = int(f"{previous_fragment}{next_fragment}")
    if amount < 1000:
        return None
    return amount


def _is_discount_identifier_context(lines: list[Mapping[str, Any]], index: int) -> bool:
    nearby_text = " ".join(
        _safe_line_text(lines[nearby_index]) or ""
        for nearby_index in range(max(index - 2, 0), min(index + 5, len(lines)))
    )
    compact = _compact_line(nearby_text)
    return any(token in compact for token in ("인증번호", "쿠폰번호", "번호"))


def _previous_split_amount_fragments(lines: list[Mapping[str, Any]], index: int, *, max_lines: int = 3) -> int | None:
    fragments: list[str] = []
    for nearby_index in range(index - 1, max(index - max_lines - 1, -1), -1):
        candidate_text = _safe_line_text(lines[nearby_index])
        if not candidate_text:
            continue
        candidate_compact = _compact_line(candidate_text)
        if candidate_compact in {"-", "－", "−", "–", "—"}:
            continue
        if _has_blocking_non_amount_label(candidate_compact):
            return None
        fragment = _amount_fragment_digits(candidate_text, allow_zero_group=True)
        if fragment is None:
            if fragments:
                break
            continue
        fragments.insert(0, fragment)
        if len(fragments) >= 2:
            amount_text = "".join(fragments[-2:])
            if len(fragments[-1]) == 3:
                amount = int(amount_text)
                if 1_000 <= amount <= 10_000_000:
                    return amount
    return None


def _previous_standalone_amount(lines: list[Mapping[str, Any]], index: int, *, max_lines: int = 3) -> int | None:
    amounts: list[int] = []
    for nearby_index in range(index - 1, max(index - max_lines - 1, -1), -1):
        candidate_text = _safe_line_text(lines[nearby_index])
        if not candidate_text:
            continue
        candidate_compact = _compact_line(candidate_text)
        if candidate_compact in {"-", "－", "−", "–", "—"}:
            continue
        if _has_blocking_non_amount_label(candidate_compact):
            break
        if not _is_standalone_amount_line(candidate_text):
            continue
        amount = _last_reasonable_amount(candidate_text)
        if amount is not None and amount >= 1_000:
            amounts.append(amount)
    return max(amounts) if amounts else None


def _previous_tax_amount_if_balanced(lines: list[Mapping[str, Any]], index: int, *, max_lines: int = 2) -> int | None:
    previous_amount = None
    for nearby_index in range(index - 1, max(index - max_lines - 1, -1), -1):
        candidate_text = _safe_line_text(lines[nearby_index])
        if not candidate_text:
            continue
        candidate_compact = _compact_line(candidate_text)
        if _has_blocking_non_amount_label(candidate_compact):
            return None
        if not _is_standalone_amount_line(candidate_text):
            continue
        amount = _last_reasonable_amount(candidate_text)
        if amount is not None and amount >= 1000:
            previous_amount = amount
            break
    if previous_amount is None:
        return None
    nearby_amounts = _nearby_standalone_amount_values(lines, index, radius=8)
    for other_amount in nearby_amounts:
        if other_amount == previous_amount:
            continue
        expected_total = previous_amount + other_amount
        if expected_total in nearby_amounts:
            return previous_amount
    return None


def _previous_vat_amount_if_balanced(lines: list[Mapping[str, Any]], index: int, *, max_lines: int = 2) -> int | None:
    amount = _previous_tax_amount_if_balanced(lines, index, max_lines=max_lines)
    if amount is None:
        return None
    nearby_amounts = _nearby_standalone_amount_values(lines, index, radius=8)
    if any(other_amount > amount * 2 for other_amount in nearby_amounts if other_amount != amount):
        return amount
    return None


def _nearby_standalone_amount_values(lines: list[Mapping[str, Any]], index: int, *, radius: int) -> list[int]:
    values: list[int] = []
    start = max(index - radius, 0)
    end = min(index + radius + 1, len(lines))
    for nearby_index in range(start, end):
        candidate_text = _safe_line_text(lines[nearby_index])
        if not candidate_text or not _is_standalone_amount_line(candidate_text):
            continue
        amount = _last_reasonable_amount(candidate_text)
        if amount is not None and amount >= 1000:
            values.append(amount)
    return values


def _is_split_vat_label(compact: str, amount_label_compact: str) -> bool:
    return compact in {"부", "부가"} and "부가" in amount_label_compact


def _split_vat_amount_between_fragments(lines: list[Mapping[str, Any]], index: int) -> int | None:
    text = _safe_line_text(lines[index])
    if not text:
        return None
    compact = _compact_line(text)
    if compact not in {"부", "부가"}:
        return None
    amount_text = _safe_line_text(lines[index + 1]) if index + 1 < len(lines) else None
    suffix_text = _safe_line_text(lines[index + 2]) if index + 2 < len(lines) else None
    if not amount_text or not suffix_text:
        return None
    if _compact_line(suffix_text) not in {"가", "세", "가세"}:
        return None
    if not _is_standalone_amount_line(amount_text):
        return None
    amount = _last_reasonable_amount(amount_text)
    if amount is None or amount < 100:
        return None
    nearby_amounts = _nearby_standalone_amount_values(lines, index, radius=8)
    if any(other_amount > amount * 2 for other_amount in nearby_amounts if other_amount != amount):
        return amount
    return None


def _has_blocking_non_amount_label(compact: str) -> bool:
    blocking_labels = (
        "사업자",
        "대표자",
        "주소",
        "판매시간",
        "승인번호",
        "카드번호",
        "카드종류",
        "테이블",
        "수량",
        "주문번호",
        "대기번호",
        "광고",
        "고객센터",
        "문의",
        "할부",
        "카드번호",
        "승인번호",
        "card번호",
        "card사명",
    )
    return any(label in compact for label in blocking_labels)


def _is_standalone_amount_line(text: str) -> bool:
    stripped = str(text or "").strip()
    if not stripped:
        return False
    without_currency = re.sub(r"[원₩\s]", "", stripped)
    return bool(re.fullmatch(r"[-−–—]?[0-9OoIl|BSㅇ]{1,3}(?:[,\\.][0-9OoIl|BSㅇ]{3})+|[-−–—]?[0-9OoIl|BSㅇ]+", without_currency))


def _amount_fragment_digits(text: str, *, allow_zero_group: bool = False) -> str | None:
    stripped = str(text or "").strip()
    if not stripped:
        return None
    if PHONE_LIKE_PATTERN.search(stripped) or CARD_LIKE_PATTERN.search(stripped):
        return None
    translated = stripped.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1", "B": "8", "S": "5", "\u3147": "0", "\uacf5": "0"}))
    digits = re.sub(r"\D", "", translated)
    if not digits:
        return None
    if allow_zero_group and set(digits) == {"0"} and len(digits) >= 3:
        return "000"
    if not re.fullmatch(r"[0-9]{1,3}", re.sub(r"\s+", "", translated)):
        return None
    if int(digits) <= 9 and not (allow_zero_group and len(digits) == 3 and set(digits) == {"0"}):
        return None
    return digits


def _leading_currency_amount_fragment(text: str) -> str | None:
    value = str(text or "").strip()
    if not value:
        return None
    if PHONE_LIKE_PATTERN.search(value) or CARD_LIKE_PATTERN.search(value):
        return None
    translated = value.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1", "B": "8", "S": "5"}))
    if not re.search(r"[\u20a9\\￦wW]", translated):
        return None
    digits = re.sub(r"\D", "", translated)
    if not (1 <= len(digits) <= 3):
        return None
    if int(digits) <= 9:
        return None
    return digits


def _trailing_currency_amount_fragment(text: str) -> str | None:
    value = str(text or "").strip()
    if not value:
        return None
    if PHONE_LIKE_PATTERN.search(value) or CARD_LIKE_PATTERN.search(value):
        return None
    translated = value.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1", "B": "8", "S": "5"}))
    digits = re.sub(r"\D", "", translated)
    if len(digits) == 3:
        return digits
    if len(digits) == 4 and digits[0] == "1":
        return digits[-3:]
    return None


def _loose_trailing_amount_fragment_digits(text: str) -> str | None:
    stripped = str(text or "").strip()
    if not stripped:
        return None
    if PHONE_LIKE_PATTERN.search(stripped) or CARD_LIKE_PATTERN.search(stripped):
        return None
    translated = stripped.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1", "B": "8", "S": "5", "\u3147": "0", "\uacf5": "0"}))
    digits = re.sub(r"\D", "", translated)
    if len(digits) != 3:
        return None
    compact = _compact_line(translated)
    if _has_blocking_non_amount_label(compact):
        return None
    return digits


def _last_reasonable_amount(text: str, *, allow_zero: bool = False) -> int | None:
    amounts = [
        amount
        for token in AMOUNT_CANDIDATE_PATTERN.findall(text or "")
        if (amount := _normalize_amount_candidate(token, source_text=text, allow_zero=allow_zero)) is not None
    ]
    if not amounts:
        return None
    return amounts[-1]


def _normalize_amount_candidate(token: object, *, source_text: str, allow_zero: bool = False) -> int | None:
    text = str(token or "").strip()
    if not text:
        return None
    if not re.search(r"\d", text):
        return None
    translated = text.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1", "B": "8", "S": "5", "\u3147": "0", "\uacf5": "0"}))
    grouped = bool(re.search(r"\d\s*[,\.]\s*\d{3}|\d\s+\d{3}", translated))
    digits = re.sub(r"\D", "", translated)
    if not digits:
        return None
    if len(digits) >= 7 and not grouped:
        return None
    if PHONE_LIKE_PATTERN.search(source_text) or CARD_LIKE_PATTERN.search(source_text):
        return None
    try:
        amount = int(digits)
    except ValueError:
        return None
    if amount == 0 and allow_zero:
        return 0
    if amount <= 9 or amount > 10_000_000:
        return None
    return -amount if translated.lstrip().startswith(("-", "－", "−", "–", "—")) else amount


def _has_any_label(compact: str, labels: tuple[str, ...]) -> bool:
    return any(label.lower().replace(" ", "") in compact for label in labels)


@lru_cache(maxsize=4096)
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
