import sys
from types import SimpleNamespace
import pytest

from app.ocr.paddle_v5_engine import PaddleV5Engine


def test_v5_bridge_uses_recognized_polygons_and_keeps_numeric_readings(monkeypatch):
    calls = []
    box = [[10,20],[80,20],[80,40],[10,40]]
    class Pipeline:
        def __init__(self, **kwargs):
            calls.append(kwargs)
        def predict(self, source, **kwargs):
            return [dict(rec_polys=[box], rec_texts=['결제금액 17,530'], rec_scores=[.99],
                         dt_polys=[[[0,0],[1,0],[1,1],[0,1]],box])]
    class Recognition:
        def __init__(self, **kwargs):
            calls.append(kwargs)
        def predict(self, source):
            return [dict(rec_text='0',rec_score=.99)]
    monkeypatch.setitem(sys.modules,'paddleocr',SimpleNamespace(PaddleOCR=Pipeline,TextRecognition=Recognition))
    engine = PaddleV5Engine(use_gpu=True)
    assert engine.ocr('synthetic.png') == [[[box,('결제금액 17,530',.99)]]]
    assert engine.ocr(object(),det=False) == [[('0',.99)]]
    assert engine.ocr(object(),det=False) == [[('0',.99)]]
    assert calls[0]['device'] == 'gpu:0'
    assert calls[0]['ocr_version'] == 'PP-OCRv5'
    assert calls[0]['use_doc_unwarping'] is False
    assert len(calls) == 2


def test_v5_bridge_rejects_mismatched_text_and_polygon_counts(monkeypatch):
    class Pipeline:
        def __init__(self, **kwargs):
            pass
        def predict(self, source, **kwargs):
            return [dict(rec_polys=[], rec_texts=['17,530'], rec_scores=[.99])]
    monkeypatch.setitem(sys.modules, 'paddleocr', SimpleNamespace(PaddleOCR=Pipeline))
    with pytest.raises(ValueError):
        PaddleV5Engine().ocr('synthetic.png')


@pytest.mark.parametrize('sdk_version,is_v5', [('2.7.3', False), ('3.3.0', True)])
def test_optional_engine_selection_follows_installed_sdk(monkeypatch, sdk_version, is_v5):
    from app.ocr.paddle_provider import _load_paddle_ocr_class
    import importlib.metadata

    legacy = object()
    monkeypatch.setitem(sys.modules, 'paddleocr', SimpleNamespace(PaddleOCR=legacy))
    monkeypatch.setattr(importlib.metadata, 'version', lambda name: sdk_version)
    assert _load_paddle_ocr_class() is (PaddleV5Engine if is_v5 else legacy)
