from hashlib import sha256
from datetime import datetime, timezone
import json

import pytest

from app.core.standard_ocr import StandardOCRResult, StandardOCRKeyValueCandidate
from scripts import evaluate_local_receipts as evaluation


def reference(tmp_path, expected, *, digest=None, name="receipt.jpg"):
    content = b"synthetic image; fake provider only"
    (tmp_path / "receipt.jpg").write_bytes(content)
    path = tmp_path / "reference.json"
    path.write_text(json.dumps([{"file_name": name, "sha256": digest or sha256(content).hexdigest(), "expected": expected}]), encoding="utf-8")
    return path


def test_reference_answers_never_enter_provider_and_report_contains_no_values(tmp_path, monkeypatch):
    calls = []

    class ObservedProvider:
        def __init__(self, **kwargs):
            pass

        def extract(self, path, **kwargs):
            calls.append((path.name, kwargs))
            return StandardOCRResult(id="synthetic", created_at=datetime.now(timezone.utc), provider="paddleocr", status="completed", source_file_name="evaluation.jpg",
                                     key_value_candidates=[StandardOCRKeyValueCandidate(key="merchant_name", candidate_type="merchant_name", value="비밀상호")])

    monkeypatch.setattr(evaluation, "PaddleOCRProvider", ObservedProvider)
    path = reference(tmp_path, {"merchant_name": "비밀상호"})
    first = evaluation.evaluate(path, tmp_path)
    path = reference(tmp_path, {"merchant_name": "다른정답"})
    second = evaluation.evaluate(path, tmp_path)
    assert first["matched_fields"] == 1 and second["matched_fields"] == 0
    assert calls == [("receipt.jpg", {"source_file_name": "evaluation.jpg"})] * 2
    serialized = json.dumps([first, second], ensure_ascii=False)
    assert all(value not in serialized for value in ("비밀상호", "다른정답", "receipt.jpg", str(tmp_path)))


@pytest.mark.parametrize("kwargs", [{"digest": "wrong"}, {"name": "../receipt.jpg"}])
def test_bad_reference_is_rejected_before_ocr(tmp_path, monkeypatch, kwargs):
    def forbidden(**kwargs):
        pytest.fail("OCR must not start for an invalid reference")
    monkeypatch.setattr(evaluation, "PaddleOCRProvider", forbidden)
    path = reference(tmp_path, {"merchant_name": "합성상호"}, **kwargs)
    with pytest.raises(ValueError):
        evaluation.evaluate(path, tmp_path)


def test_reference_cannot_redefine_supported_fields(tmp_path):
    path = reference(tmp_path, {"raw_text": "forbidden"})
    with pytest.raises(ValueError):
        evaluation.evaluate(path, tmp_path)


@pytest.mark.parametrize("value", ["??", "\ufffd\ufffd", ""])
def test_corrupted_or_empty_reference_is_rejected_before_ocr(tmp_path, monkeypatch, value):
    def forbidden(**kwargs):
        pytest.fail("OCR must not start with a corrupted reference")

    monkeypatch.setattr(evaluation, "PaddleOCRProvider", forbidden)
    path = reference(tmp_path, {"merchant_name": value})
    with pytest.raises(ValueError, match="invalid_reference"):
        evaluation.evaluate(path, tmp_path)


@pytest.mark.parametrize('expected', [
    {'business_number': '010-1234-5678'},
    {'business_number': '123-45-6789'},
    {'transaction_date': '2028-02-30'},
    {'transaction_date': '2028/02/29'},
])
def test_invalid_field_reference_fails_before_ocr(tmp_path, monkeypatch, expected):
    def forbidden(**kwargs):
        pytest.fail('invalid reference must be rejected before engine initialization')
    monkeypatch.setattr(evaluation, 'PaddleOCRProvider', forbidden)
    with pytest.raises(ValueError):
        evaluation.evaluate(reference(tmp_path, expected), tmp_path)


def test_duplicate_image_cannot_inflate_the_reference_score(tmp_path, monkeypatch):
    path = reference(tmp_path, {'merchant_name': '새봄공방'})
    rows = json.loads(path.read_text(encoding='utf-8'))
    path.write_text(json.dumps(rows*2), encoding='utf-8')
    def forbidden(**kwargs):
        pytest.fail('duplicate image must be rejected before OCR')
    monkeypatch.setattr(evaluation, 'PaddleOCRProvider', forbidden)
    with pytest.raises(ValueError, match='duplicate_reference_image'):
        evaluation.evaluate(path, tmp_path)
