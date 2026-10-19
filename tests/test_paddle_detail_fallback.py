from PIL import Image

from app.ocr.paddle_provider import PaddleOCRProvider, _merge_missing_candidate_hints
from app.parser.normalizers import normalize_date


def item(text, y):
    return [[[0, y], [90, y], [90, y + 20], [0, y + 20]], (text, 0.99)]


def test_tiled_read_keeps_boundary_row_once_and_restores_coordinates(tmp_path):
    source = tmp_path / "receipt.png"
    Image.new("RGB", (100, 2500), "white").save(source)

    class Engine:
        calls = 0

        def ocr(self, path, cls=False):
            self.calls += 1
            if self.calls == 1:
                return [[item("부가세 23", 990)]]  # Center belongs to the following band.
            if self.calls == 2:
                return [[item("부가세 23", 90)]]
            return [[]]

    engine = Engine()
    result = PaddleOCRProvider()._tiled_image_result(engine, source, use_textline_orientation=False)
    assert engine.calls == 3
    assert len(result["lines"]) == 1
    assert result["lines"][0]["bbox"][0][1] == 990
    assert result["key_value_candidates"][0]["value"] == "23"


def test_tiled_read_is_bounded_to_eight_bands(tmp_path):
    source = tmp_path / "tall.png"
    Image.new("RGB", (100, 10_000), "white").save(source)

    class Engine:
        calls = 0

        def ocr(self, path, cls=False):
            self.calls += 1
            return [[]]

    engine = Engine()
    PaddleOCRProvider()._tiled_image_result(engine, source, use_textline_orientation=False)
    assert engine.calls == 8


def test_missing_tax_merge_retains_values_and_resolves_source_id_collisions():
    primary = {"lines": [{"block_id": "same", "text": "공급가액 1000"}],
               "key_value_candidates": [{"candidate_type": "supply_amount", "value": "1000"}]}
    extra = {"lines": [{"block_id": "same", "text": "부가세 23"}],
             "key_value_candidates": [{"candidate_type": "supply_amount", "value": "2000"},
                                      {"candidate_type": "vat_amount", "value": "23", "source_block_ids": ["same"]}]}
    merged = _merge_missing_candidate_hints(primary, extra, allowed_types={"supply_amount", "vat_amount"})
    assert merged["key_value_candidates"][0]["value"] == "1000"
    candidate = merged["key_value_candidates"][1]
    assert candidate["source_block_ids"] != ["same"]
    blocks = {line["block_id"]: line for line in merged["lines"]}
    assert blocks[candidate["source_block_ids"][0]]["text"] == "부가세 23"
    assert len(primary["lines"]) == 1


def test_provider_fills_missing_tax_without_overwriting_existing_fields(tmp_path):
    source = tmp_path / "receipt.png"
    Image.new("RGB", (100, 2300), "white").save(source)

    class Engine:
        def __init__(self, **kwargs):
            pass

        def ocr(self, path, cls=False):
            with Image.open(path) as image:
                full = image.height == 2300
            texts = ["상호명: 새빛문구", "합계 12,345", "공급가액 10,000"] if full else ["공급가액 20,000", "부가세 23"]
            return [[item(text, index * 40) for index, text in enumerate(texts)]]

    result = PaddleOCRProvider(ocr_factory=Engine).extract(source)
    values = {candidate.candidate_type: candidate.value for candidate in result.key_value_candidates}
    assert values["total_amount"] == "12345"
    assert values["supply_amount"] == "10000"
    assert values["vat_amount"] == "23"
    assert "paddle_tiled_tax_candidate_fallback" in result.warnings
    block_ids = {block.block_id for block in result.text_blocks}
    assert all(set(candidate.source_block_ids) <= block_ids for candidate in result.key_value_candidates)


def test_failed_tax_reread_preserves_completed_primary_and_hides_exception(tmp_path, monkeypatch):
    source = tmp_path / "receipt.png"
    Image.new("RGB", (100, 200), "white").save(source)

    class Engine:
        def __init__(self, **kwargs):
            pass

        def ocr(self, path, cls=False):
            return [[item("상호명: 새빛문구", 0), item("합계 12,345", 40)]]

    def fail(*args, **kwargs):
        raise RuntimeError("private-error-details")

    monkeypatch.setattr(PaddleOCRProvider, "_tiled_image_result", fail)
    result = PaddleOCRProvider(ocr_factory=Engine).extract(source)
    assert result.status == "completed"
    assert "paddle_tiled_tax_fallback_skipped" in result.warnings
    assert "private-error-details" not in result.model_dump_json()


def test_complete_explicit_tax_does_not_trigger_tiled_read(tmp_path, monkeypatch):
    source = tmp_path / "receipt.png"
    Image.new("RGB", (100, 200), "white").save(source)

    class Engine:
        def __init__(self, **kwargs):
            pass

        def ocr(self, path, cls=False):
            return [[item(text, i * 35) for i, text in enumerate(
                ("상호명: 새빛문구", "합계 12,345", "공급가액 0", "부가세 0", "2028-09-17"))]]

    calls = []
    monkeypatch.setattr(PaddleOCRProvider, "_tiled_image_result", lambda *a, **kw: calls.append(True))
    result = PaddleOCRProvider(ocr_factory=Engine).extract(source)
    assert result.status == "completed"
    assert not calls


def test_tiled_read_recovers_missing_date_without_overwriting_observed_fields(tmp_path, monkeypatch):
    source = tmp_path / "receipt.png"
    Image.new("RGB", (100, 2300), "white").save(source)

    class Engine:
        def __init__(self, **kwargs):
            pass

        def ocr(self, path, cls=False):
            return [[item(text, i * 40) for i, text in enumerate(
                ("상호명: 새빛문구", "합계 12,345", "공급가액 0", "부가세 0"))]]

    provider = PaddleOCRProvider(ocr_factory=Engine)
    extra = provider._sanitize_result([[item(text, i * 40) for i, text in enumerate(
        ("승인시간 20280917123456", "상호명: 다른문구", "합계 54,321", "부가세 456"))]])
    monkeypatch.setattr(provider, "_tiled_image_result", lambda *a, **kw: extra)
    values = {candidate.candidate_type: candidate.value for candidate in provider.extract(source).key_value_candidates}
    assert normalize_date(values["transaction_date"]).isoformat() == "2028-09-17"
    assert values["merchant_name"] == "새빛문구"
    assert values["total_amount"] == "12345"
    assert values["vat_amount"] == "0"


def test_rotation_fallback_adds_missing_fields_without_losing_primary_identity(tmp_path, monkeypatch):
    source = tmp_path / "receipt.png"
    Image.new("RGB", (100, 200), "white").save(source)

    class Engine:
        def __init__(self, **kwargs):
            pass

        def ocr(self, path, cls=False):
            return [[item("상호명: 새빛문구", 0)]]

    provider = PaddleOCRProvider(ocr_factory=Engine)
    extra = provider._sanitize_result([[item("합계 12,345", 0), item("카드결제 12,345", 40)]])
    monkeypatch.setattr(provider, "_best_rotated_image_result", lambda *a, **kw: extra)
    monkeypatch.setattr(provider, "_best_enhanced_image_result", lambda *a, **kw: None)
    monkeypatch.setattr(provider, "_best_detail_crop_result", lambda *a, **kw: None)
    monkeypatch.setattr(provider, "_tiled_image_result", lambda *a, **kw: {"key_value_candidates": []})
    result = provider.extract(source)
    values = {candidate.candidate_type: candidate.value for candidate in result.key_value_candidates}
    assert values["merchant_name"] == "새빛문구"
    assert values["total_amount"] == "12345"


def test_fine_date_retry_cannot_fill_missing_tax(tmp_path, monkeypatch):
    source = tmp_path / "receipt.png"
    Image.new("RGB", (100, 2300), "white").save(source)

    class Engine:
        def __init__(self, **kwargs):
            pass

        def ocr(self, path, cls=False):
            return [[item("상호명: 새빛문구", 0), item("합계 12,345", 40)]]

    provider = PaddleOCRProvider(ocr_factory=Engine)
    extra = provider._sanitize_result([[item("승인시간 20280917123456", 0), item("부가세 456", 40)]])
    calls = []

    def tiled(*args, band_height=1000, **kwargs):
        calls.append(band_height)
        return extra if band_height == 500 else {"key_value_candidates": []}

    monkeypatch.setattr(provider, "_tiled_image_result", tiled)
    result = provider.extract(source)
    values = {candidate.candidate_type: candidate.value for candidate in result.key_value_candidates}
    assert calls == [1000, 500]
    assert normalize_date(values["transaction_date"]).isoformat() == "2028-09-17"
    assert "vat_amount" not in values
    assert "paddle_tiled_date_candidate_fallback" in result.warnings


def test_fine_date_retry_failure_keeps_completed_result_and_private_error_hidden(tmp_path, monkeypatch):
    source = tmp_path / "receipt.png"
    Image.new("RGB", (100, 2300), "white").save(source)

    class Engine:
        def __init__(self, **kwargs):
            pass

        def ocr(self, path, cls=False):
            return [[item(text, i * 40) for i, text in enumerate(
                ("상호명: 새빛문구", "합계 12,345", "공급가액 0", "부가세 0"))]]

    def fail(*args, **kwargs):
        raise RuntimeError("private-date-error")

    monkeypatch.setattr(PaddleOCRProvider, "_tiled_image_result", fail)
    result = PaddleOCRProvider(ocr_factory=Engine).extract(source)
    assert result.status == "completed"
    assert "paddle_tiled_date_fallback_skipped" in result.warnings
    assert "private-date-error" not in result.model_dump_json()
