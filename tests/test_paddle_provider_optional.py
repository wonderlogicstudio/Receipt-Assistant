from __future__ import annotations

import ast
import json
import re
import sys
import types
from pathlib import Path

from app.core.standard_ocr import StandardOCRResult
from app.ocr.paddle_provider import (
    PaddleOCRProvider,
    PaddleOCRUnavailable,
    get_paddle_device_diagnostics,
)
import app.ocr.paddle_provider as paddle_provider_module


FORBIDDEN_TEXT_PATTERNS = [
    r"raw_json",
    r"raw_text",
    r"provider_raw_response",
    r"full_ocr_text",
    r"image_path",
    r"model_path",
    r"absolute_path",
    r"local_file_path",
    r"api_key",
    r"secret",
    r"token",
    r"password",
    r"[A-Za-z]:\\",
    r"/Users/",
    r"/home/",
    r"/var/",
    r"/tmp/",
    r"\b\d{13,19}\b",
    r"\b\d{6}-\d{7}\b",
]


def result_text(result: StandardOCRResult) -> str:
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False, default=str)


def assert_no_forbidden_output(result: StandardOCRResult) -> None:
    text = result_text(result)
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        assert not re.search(pattern, text, flags=re.IGNORECASE), pattern


def test_paddle_provider_import_and_instantiation_do_not_require_paddleocr() -> None:
    provider = PaddleOCRProvider()

    assert provider.provider_name == "paddleocr"
    assert provider.provider_alias == "paddle"


def test_paddle_provider_has_no_top_level_paddleocr_import() -> None:
    source = Path("app/ocr/paddle_provider.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in tree.body:
        if isinstance(node, ast.Import):
            assert all(alias.name != "paddleocr" for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module != "paddleocr"


def test_missing_paddleocr_returns_failed_standard_result(monkeypatch) -> None:
    def raise_unavailable() -> object:
        raise PaddleOCRUnavailable("paddle_not_installed")

    monkeypatch.setattr(paddle_provider_module, "_load_paddle_ocr_class", raise_unavailable)

    result = PaddleOCRProvider().extract("sample_receipt.png")

    assert isinstance(result, StandardOCRResult)
    assert result.provider == "paddleocr"
    assert result.status == "failed"
    assert result.diagnostic_code == "paddle_not_installed"
    assert result.warnings == ["paddle_not_installed", "paddle_status:failed"]
    assert result.text_blocks == []
    assert result.key_value_candidates == []
    assert result.table_candidates == []
    assert_no_forbidden_output(result)
    assert {"raw_response", "paddle_raw_output", "image_path", "model_path"}.isdisjoint(
        result.provider_fields
    )


def test_paddle_device_diagnostics_returns_safe_mapping(monkeypatch) -> None:
    fake_paddle = types.SimpleNamespace(
        device=types.SimpleNamespace(
            is_compiled_with_cuda=lambda: True,
            get_device=lambda: "gpu:0",
        )
    )
    monkeypatch.setitem(sys.modules, "paddle", fake_paddle)

    diagnostics = get_paddle_device_diagnostics()

    assert diagnostics == {
        "device": "gpu:0",
        "cuda_compiled": True,
        "diagnostic_code": None,
    }


def test_paddle_device_diagnostics_handles_runtime_errors(monkeypatch) -> None:
    class BrokenDevice:
        @staticmethod
        def is_compiled_with_cuda() -> bool:
            raise RuntimeError("hidden runtime detail")

        @staticmethod
        def get_device() -> str:
            raise RuntimeError("hidden runtime detail")

    monkeypatch.setitem(sys.modules, "paddle", types.SimpleNamespace(device=BrokenDevice()))

    diagnostics = get_paddle_device_diagnostics()

    assert diagnostics["device"] == "unknown"
    assert diagnostics["cuda_compiled"] is None
    assert diagnostics["diagnostic_code"] == "paddle_device_diagnostic_failed"


def test_pdf_input_returns_unsupported_without_loading_paddleocr(monkeypatch) -> None:
    def fail_if_loaded() -> object:
        raise AssertionError("paddleocr loader should not be called for PDF input")

    monkeypatch.setattr(paddle_provider_module, "_load_paddle_ocr_class", fail_if_loaded)

    result = PaddleOCRProvider().extract("sample_receipt.pdf")

    assert result.status == "failed"
    assert result.diagnostic_code == "paddle_pdf_not_supported"
    assert result.text_blocks == []
    assert_no_forbidden_output(result)


def test_unsupported_non_image_input_returns_safe_result(monkeypatch) -> None:
    def fail_if_loaded() -> object:
        raise AssertionError("paddleocr loader should not be called for non-image input")

    monkeypatch.setattr(paddle_provider_module, "_load_paddle_ocr_class", fail_if_loaded)

    result = PaddleOCRProvider().extract("card_statement.csv")

    assert result.status == "skipped"
    assert result.diagnostic_code == "paddle_not_ocr_target"
    assert_no_forbidden_output(result)


def test_fake_paddleocr_success_returns_standard_result(tmp_path) -> None:
    image_path = tmp_path / "receipt.png"
    image_path.write_bytes(b"fake image bytes")

    class FakePaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        def ocr(self, path: str, cls: bool = False) -> list:
            assert path.endswith("receipt.png")
            assert cls is False
            return [
                [
                    [
                        [[10, 10], [200, 10], [200, 40], [10, 40]],
                        ("상호 샘플상점", 0.91),
                    ],
                    [
                        [[10, 60], [260, 60], [260, 90], [10, 90]],
                        ("총금액 12000", 0.89),
                    ],
                ]
            ]

    result = PaddleOCRProvider(ocr_factory=FakePaddleOCR).extract(
        image_path,
        source_file_id="fake-paddle-source",
        source_file_name="fake_receipt.png",
    )

    assert result.provider_fields["has_angle_classifier"] is False
    assert result.provider == "paddleocr"
    assert result.provider_version == "optional"
    assert result.engine_runtime == "pc_local"
    assert result.status == "completed"
    assert result.source_file_name == "fake_receipt.png"
    assert [block.text for block in result.text_blocks] == ["상호 샘플상점", "총금액 12000"]
    assert result.text_blocks[0].bbox == [10.0, 10.0, 200.0, 10.0, 200.0, 40.0, 10.0, 40.0]
    assert result.provider_fields["adapter_version"] == "paddle-standard-adapter-v1"
    assert result.provider_fields["provider_family"] == "paddleocr"
    assert result.provider_fields["input_type"] == "image"
    assert result.provider_fields["provider"] == "paddle"
    assert result.provider_fields["device"] == "unknown"
    assert result.provider_fields["cuda_compiled"] is None
    assert result.provider_fields["image_extension"] == ".png"
    assert result.provider_fields["status"] == "completed"
    assert result.provider_fields["diagnostic_code"] == "completed"
    for key in ("init_elapsed_ms", "ocr_elapsed_ms", "total_elapsed_ms"):
        assert isinstance(result.provider_fields[key], int)
        assert result.provider_fields[key] >= 0
    assert_no_forbidden_output(result)


def test_orientation_fallback_requires_identity_and_amount_evidence() -> None:
    assert paddle_provider_module._should_try_orientation_fallback({"key_value_candidates": []})
    assert paddle_provider_module._should_try_orientation_fallback({"key_value_candidates": [{"candidate_type": "approval_number"}]})
    assert paddle_provider_module._should_try_orientation_fallback(
        {"key_value_candidates": [{"candidate_type": "transaction_date"}]}
    )
    assert paddle_provider_module._should_try_orientation_fallback(
        {"key_value_candidates": [{"candidate_type": "total_amount"}]}
    )


def test_quality_score_prefers_core_candidates_over_line_count_only() -> None:
    noisy_many_lines = {
        "lines": [{"text": f"noise-{index}"} for index in range(120)],
        "key_value_candidates": [{"candidate_type": "approval_number"}],
    }
    core_candidate = {
        "lines": [{"text": "merchant"}, {"text": "date"}],
        "key_value_candidates": [
            {"candidate_type": "merchant_name"},
            {"candidate_type": "transaction_date"},
            {"candidate_type": "business_number"},
        ],
    }

    assert paddle_provider_module._quality_score(core_candidate) > paddle_provider_module._quality_score(noisy_many_lines)


def test_merge_missing_candidate_hints_preserves_existing_values() -> None:
    primary = {
        "key_value_candidates": [
            {
                "candidate_type": "total_amount",
                "key": "total_amount",
                "value": "10000",
                "normalized_value": "10000",
            }
        ]
    }
    supplemental = {
        "key_value_candidates": [
            {
                "candidate_type": "total_amount",
                "key": "total_amount",
                "value": "15000",
                "normalized_value": "15000",
            },
            {
                "candidate_type": "business_number",
                "key": "business_number",
                "value": "205-39-03897",
                "normalized_value": "205-39-03897",
            },
        ]
    }

    merged = paddle_provider_module._merge_missing_candidate_hints(
        primary,
        supplemental,
        allowed_types={"total_amount", "business_number"},
    )

    values = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in merged["key_value_candidates"]
    }
    assert values["total_amount"] == "10000"
    assert values["business_number"] == "205-39-03897"


def test_real_paddle_factory_is_cached_across_provider_instances(monkeypatch, tmp_path) -> None:
    paddle_provider_module._clear_paddle_ocr_cache_for_tests()
    image_path = tmp_path / "receipt.png"
    image_path.write_bytes(b"fake image bytes")
    init_calls = 0

    class FakePaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            nonlocal init_calls
            init_calls += 1

        def ocr(self, path: str, cls: bool = False) -> dict:
            return {
                "rec_texts": ["SAMPLE CAFE"],
                "rec_scores": [0.98],
                "dt_polys": [[[10, 10], [220, 10], [220, 42], [10, 42]]],
            }

    monkeypatch.setattr(paddle_provider_module, "_load_paddle_ocr_class", lambda: FakePaddleOCR)
    monkeypatch.setattr(
        paddle_provider_module,
        "get_paddle_device_diagnostics",
        lambda: {"device": "cpu", "cuda_compiled": False, "diagnostic_code": None},
    )
    monkeypatch.setattr(
        paddle_provider_module.importlib.util,
        "find_spec",
        lambda name: object() if name == "paddle" else object(),
    )

    first_result = PaddleOCRProvider().extract(image_path, source_file_name="receipt.png")
    second_result = PaddleOCRProvider().extract(image_path, source_file_name="receipt.png")

    assert init_calls == 1
    assert first_result.status == "completed"
    assert second_result.status == "completed"
    assert first_result.provider_fields["device"] == "cpu"
    assert second_result.provider_fields["device"] == "cpu"
    assert_no_forbidden_output(first_result)
    assert_no_forbidden_output(second_result)
    paddle_provider_module._clear_paddle_ocr_cache_for_tests()


def test_paddle_provider_reuses_ocr_instance_for_multiple_images(tmp_path) -> None:
    first_image_path = tmp_path / "receipt_1.png"
    second_image_path = tmp_path / "receipt_2.png"
    first_image_path.write_bytes(b"fake image bytes")
    second_image_path.write_bytes(b"fake image bytes")
    init_calls = 0
    ocr_calls: list[str] = []

    class FakePaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            nonlocal init_calls
            init_calls += 1
            self.kwargs = kwargs

        def ocr(self, path: str, cls: bool = True) -> dict:
            ocr_calls.append(Path(path).name)
            return {
                "rec_texts": ["SAMPLE CAFE", "2026-06-10", "TOTAL 12000", "CARD"],
                "rec_scores": [0.98, 0.97, 0.96, 0.95],
                "dt_polys": [
                    [[10, 10], [220, 10], [220, 42], [10, 42]],
                    [[10, 50], [220, 50], [220, 82], [10, 82]],
                    [[10, 90], [260, 90], [260, 122], [10, 122]],
                    [[10, 130], [260, 130], [260, 162], [10, 162]],
                ],
            }

    provider = PaddleOCRProvider(ocr_factory=FakePaddleOCR)

    first_result = provider.extract(first_image_path, source_file_name="receipt_1.png")
    second_result = provider.extract(second_image_path, source_file_name="receipt_2.png")

    assert init_calls == 1
    assert ocr_calls[:2] == ["receipt_1.png", "receipt_2.png"]
    assert first_result.status == "completed"
    assert second_result.status == "completed"
    assert_no_forbidden_output(first_result)
    assert_no_forbidden_output(second_result)


def test_fake_sanitized_mapping_uses_paddle_standard_adapter(tmp_path) -> None:
    image_path = tmp_path / "receipt.jpg"
    image_path.write_bytes(b"fake image bytes")

    class FakePaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            pass

        def ocr(self, path: str, cls: bool = True) -> dict:
            return {
                "engine": "paddleocr",
                "engine_version": "fake",
                "status": "succeeded",
                "input_type": "image",
                "image_count": 1,
                "lines": [
                    {
                        "block_id": "fake-line-1",
                        "text": "공급가액 10909",
                        "confidence": 0.9,
                        "bbox": [[10, 10], [200, 10], [200, 40], [10, 40]],
                    }
                ],
                "key_value_candidates": [
                    {
                        "key": "supply_amount",
                        "value": "10909",
                        "normalized_value": "10909",
                        "candidate_type": "supply_amount",
                        "source_block_ids": ["fake-line-1"],
                    }
                ],
            }

    result = PaddleOCRProvider(ocr_factory=FakePaddleOCR).extract(
        image_path,
        source_file_id="fake-paddle-source",
        source_file_name="receipt.png",
    )

    assert result.provider == "paddleocr"
    assert result.provider_version == "fake"
    assert result.key_value_candidates[0].candidate_type == "supply_amount"
    assert result.key_value_candidates[0].normalized_value == "10909"
    assert_no_forbidden_output(result)


def test_paddle_ocr_v3_result_shape_is_sanitized_to_text_blocks(tmp_path) -> None:
    image_path = tmp_path / "receipt.png"
    image_path.write_bytes(b"fake image bytes")

    class FakePaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            pass

        def ocr(self, path: str, **kwargs: object) -> dict:
            return {
                "input_path": str(image_path),
                "rec_texts": ["SAMPLE CAFE", "TOTAL 12000"],
                "rec_scores": [0.98, 0.95],
                "dt_polys": [
                    [[10, 10], [220, 10], [220, 42], [10, 42]],
                    [[10, 60], [240, 60], [240, 92], [10, 92]],
                ],
            }

    result = PaddleOCRProvider(ocr_factory=FakePaddleOCR).extract(
        image_path,
        source_file_name="receipt.png",
    )

    assert result.status == "completed"
    assert result.diagnostic_code is None
    assert [block.text for block in result.text_blocks] == ["SAMPLE CAFE", "TOTAL 12000"]
    assert result.text_blocks[0].confidence == 0.98
    assert result.text_blocks[0].bbox == [10.0, 10.0, 220.0, 10.0, 220.0, 42.0, 10.0, 42.0]
    assert_no_forbidden_output(result)


def test_paddle_provider_generates_safe_candidate_hints_from_lines(tmp_path) -> None:
    image_path = tmp_path / "receipt.png"
    image_path.write_bytes(b"fake image bytes")

    class FakePaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            pass

        def ocr(self, path: str, **kwargs: object) -> dict:
            return {
                "rec_texts": [
                    "SAMPLE CAFE",
                    "2026-02-16 12:30",
                    "사업자등록번호 123-45-67891",
                    "카드결제 35,700",
                ],
                "rec_scores": [0.98, 0.95, 0.94, 0.96],
                "dt_polys": [
                    [[10, 10], [220, 10], [220, 42], [10, 42]],
                    [[10, 50], [220, 50], [220, 82], [10, 82]],
                    [[10, 90], [260, 90], [260, 122], [10, 122]],
                    [[10, 130], [260, 130], [260, 162], [10, 162]],
                ],
            }

    result = PaddleOCRProvider(ocr_factory=FakePaddleOCR).extract(
        image_path,
        source_file_name="receipt.png",
    )

    candidates = {candidate.candidate_type: candidate.normalized_value for candidate in result.key_value_candidates}
    assert candidates["transaction_date"] == "2026-02-16 12:30"
    assert candidates["business_number"] == "123-45-67891"
    assert candidates["payment_method"] == "카드"
    assert candidates["paid_amount"] == "35700"
    assert candidates["total_amount"] == "35700"
    assert "paddle_candidate_hints_generated" in result.warnings
    assert_no_forbidden_output(result)


def test_paddle_provider_does_not_guess_total_from_unlabeled_amounts(tmp_path) -> None:
    image_path = tmp_path / "receipt.png"
    image_path.write_bytes(b"fake image bytes")

    class FakePaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            pass

        def ocr(self, path: str, **kwargs: object) -> dict:
            return {
                "rec_texts": ["SAMPLE STORE", "item 1 2,000", "item 2 12,000"],
                "rec_scores": [0.97, 0.93, 0.94],
            }

    result = PaddleOCRProvider(ocr_factory=FakePaddleOCR).extract(
        image_path,
        source_file_id="fake-paddle-source",
        source_file_name="receipt.png",
    )

    candidates = {candidate.candidate_type: candidate.normalized_value for candidate in result.key_value_candidates}
    assert "merchant_name" not in candidates
    assert "total_amount" not in candidates
    assert_no_forbidden_output(result)


def test_paddle_ocr_v3_predict_is_used_when_ocr_method_is_not_implemented(tmp_path) -> None:
    image_path = tmp_path / "receipt.png"
    image_path.write_bytes(b"fake image bytes")
    calls: list[str] = []

    class FakePaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            pass

        def ocr(self, path: str, **kwargs: object) -> dict:
            calls.append("ocr")
            raise NotImplementedError("use predict")

        def predict(self, path: str, **kwargs: object) -> dict:
            calls.append("predict")
            return {
                "rec_texts": ["SAMPLE CAFE", "TOTAL 12000"],
                "rec_scores": [0.98, 0.95],
                "dt_polys": [
                    [[10, 10], [220, 10], [220, 42], [10, 42]],
                    [[10, 60], [240, 60], [240, 92], [10, 92]],
                ],
            }

    result = PaddleOCRProvider(ocr_factory=FakePaddleOCR).extract(
        image_path,
        source_file_name="receipt.png",
    )

    assert calls == ["ocr", "predict"]
    assert result.status == "completed"
    assert [block.text for block in result.text_blocks] == ["SAMPLE CAFE", "TOTAL 12000"]
    assert_no_forbidden_output(result)


def test_paddle_ocr_legacy_call_not_implemented_falls_back_to_predict(tmp_path) -> None:
    image_path = tmp_path / "receipt.png"
    image_path.write_bytes(b"fake image bytes")
    calls: list[str] = []

    class FakePaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            pass

        def ocr(self, path: str, **kwargs: object) -> dict:
            if "use_doc_orientation_classify" in kwargs:
                calls.append("modern_ocr")
                raise TypeError("legacy signature")
            calls.append("legacy_ocr")
            raise NotImplementedError("use predict")

        def predict(self, path: str, **kwargs: object) -> dict:
            calls.append("predict")
            return {
                "rec_texts": ["SAMPLE CAFE"],
                "rec_scores": [0.98],
                "dt_polys": [[[10, 10], [220, 10], [220, 42], [10, 42]]],
            }

    result = PaddleOCRProvider(ocr_factory=FakePaddleOCR).extract(
        image_path,
        source_file_name="receipt.png",
    )

    assert calls == ["legacy_ocr", "predict"]
    assert result.status == "completed"
    assert result.text_blocks[0].text == "SAMPLE CAFE"
    assert_no_forbidden_output(result)


def test_value_error_retries_with_normalized_png_image(tmp_path) -> None:
    image_path = tmp_path / "receipt.jpg"
    image_path.write_bytes(b"fake image bytes")
    calls: list[str] = []

    class FakePaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            pass

        def ocr(self, path: str, cls: bool = True) -> dict:
            calls.append(Path(path).suffix.lower())
            if len(calls) == 1:
                raise ValueError("decode failed")
            return {
                "rec_texts": ["SAMPLE CAFE"],
                "rec_scores": [0.98],
                "dt_polys": [[[10, 10], [220, 10], [220, 42], [10, 42]]],
            }

    from PIL import Image

    Image.new("RGB", (120, 80), "white").save(image_path)

    result = PaddleOCRProvider(ocr_factory=FakePaddleOCR).extract(
        image_path,
        source_file_name="receipt.jpg",
    )

    assert calls == [".jpg", ".png"]
    assert result.status == "completed"
    assert result.text_blocks[0].text == "SAMPLE CAFE"
    assert "paddle_image_normalization_fallback" in result.warnings
    assert_no_forbidden_output(result)


def test_paddle_provider_disables_sdk_console_logging(tmp_path) -> None:
    image_path = tmp_path / "receipt.png"
    image_path.write_bytes(b"fake image bytes")
    init_kwargs: dict[str, object] = {}

    class FakePaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            init_kwargs.update(kwargs)

        def ocr(self, path: str, cls: bool = True) -> list:
            return [
                [
                    [
                        [[10, 10], [200, 10], [200, 40], [10, 40]],
                        ("SAMPLE CAFE", 0.91),
                    ]
                ]
            ]

    result = PaddleOCRProvider(ocr_factory=FakePaddleOCR, use_angle_cls=True).extract(image_path)

    assert init_kwargs["show_log"] is False
    assert result.status == "completed"


def test_not_implemented_orientation_error_retries_without_textline_orientation(tmp_path) -> None:
    image_path = tmp_path / "receipt.png"
    image_path.write_bytes(b"fake image bytes")
    calls: list[bool | None] = []

    class FakePaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            self.use_textline_orientation = kwargs.get("use_angle_cls")

        def ocr(self, path: str, **kwargs: object) -> dict:
            calls.append(self.use_textline_orientation)
            if self.use_textline_orientation:
                raise NotImplementedError("runtime op is not supported")
            return {
                "rec_texts": ["SAMPLE CAFE"],
                "rec_scores": [0.97],
                "dt_polys": [[[10, 10], [200, 10], [200, 40], [10, 40]]],
            }

    result = PaddleOCRProvider(ocr_factory=FakePaddleOCR, use_angle_cls=True).extract(image_path)

    assert calls == [True, False]
    assert result.status == "completed"
    assert result.diagnostic_code is None
    assert result.text_blocks[0].text == "SAMPLE CAFE"
    assert "paddle_textline_orientation_fallback" in result.warnings
    assert_no_forbidden_output(result)


def test_runtime_error_returns_non_sensitive_failed_result(tmp_path) -> None:
    image_path = tmp_path / "receipt.jpeg"
    image_path.write_bytes(b"fake image bytes")

    class BrokenPaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            pass

        def ocr(self, path: str, cls: bool = True) -> list:
            raise RuntimeError("do not expose this traceback")

    result = PaddleOCRProvider(ocr_factory=BrokenPaddleOCR).extract(image_path)

    assert result.status == "failed"
    assert result.diagnostic_code == "paddle_runtime_error"
    assert result.provider_fields["diagnostic_detail_code"] == "runtime_error"
    assert "detail:runtime_error" in result.warnings
    assert "traceback" not in result_text(result).lower()
    assert_no_forbidden_output(result)


def test_ocr_creation_error_returns_non_sensitive_failed_result(tmp_path) -> None:
    image_path = tmp_path / "receipt.png"
    image_path.write_bytes(b"fake image bytes")

    class BrokenFactory:
        def __init__(self, **kwargs: object) -> None:
            raise RuntimeError("do not expose constructor traceback")

    result = PaddleOCRProvider(ocr_factory=BrokenFactory).extract(image_path)

    assert result.status == "failed"
    assert result.diagnostic_code == "paddle_runtime_error"
    assert result.provider_fields["diagnostic_detail_code"] == "runtime_error"
    assert "detail:runtime_error" in result.warnings
    assert "traceback" not in result_text(result).lower()
    assert_no_forbidden_output(result)


def test_missing_paddle_runtime_returns_safe_diagnostic(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "receipt.png"
    image_path.write_bytes(b"fake image bytes")

    class FakePaddleOCR:
        pass

    monkeypatch.setattr(paddle_provider_module, "_load_paddle_ocr_class", lambda: FakePaddleOCR)
    monkeypatch.setattr(paddle_provider_module.importlib.util, "find_spec", lambda name: None if name == "paddle" else object())

    result = PaddleOCRProvider().extract(image_path)

    assert result.status == "failed"
    assert result.diagnostic_code == "paddle_runtime_missing"
    assert_no_forbidden_output(result)


def test_gpu_request_without_cuda_returns_safe_diagnostic(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "receipt.png"
    image_path.write_bytes(b"fake image bytes")

    def fail_if_loaded() -> object:
        raise AssertionError("PaddleOCR should not be initialized when CUDA is unavailable")

    monkeypatch.setattr(paddle_provider_module, "_load_paddle_ocr_class", fail_if_loaded)
    monkeypatch.setattr(
        paddle_provider_module,
        "get_paddle_device_diagnostics",
        lambda: {"device": "cpu", "cuda_compiled": False, "diagnostic_code": None},
    )

    result = PaddleOCRProvider(use_gpu=True).extract(image_path, source_file_name="receipt.png")

    assert result.status == "failed"
    assert result.diagnostic_code == "paddle_cuda_not_available"
    assert result.provider_fields["device"] == "cpu"
    assert result.provider_fields["cuda_compiled"] is False
    assert result.provider_fields["diagnostic_code"] == "paddle_cuda_not_available"
    assert_no_forbidden_output(result)


def test_source_file_name_is_file_name_only_even_for_path_input(tmp_path) -> None:
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    image_path = nested_dir / "receipt.png"
    image_path.write_bytes(b"fake image bytes")

    class EmptyPaddleOCR:
        def __init__(self, **kwargs: object) -> None:
            pass

        def ocr(self, path: str, cls: bool = True) -> list:
            return []

    result = PaddleOCRProvider(ocr_factory=EmptyPaddleOCR).extract(image_path)

    assert result.source_file_name == "receipt.png"
    assert result.diagnostic_code == "paddle_no_text_detected"
    assert_no_forbidden_output(result)
