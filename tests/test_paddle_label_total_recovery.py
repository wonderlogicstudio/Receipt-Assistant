import pytest
from PIL import Image

from app.ocr.paddle_provider import PaddleOCRProvider, build_paddle_candidate_hints_from_safe_lines


def positioned(text, x, y, width=70):
    return dict(block_id=f'{x}-{y}', text=text, confidence=.99,
                bbox=[[x, y], [x+width, y], [x+width, y+24], [x, y+24]])


def test_merchant_stops_at_the_next_explicit_field_on_the_same_row():
    lines = [positioned('상호:', 0, 0), positioned('새봄공방', 100, 0),
             positioned('대표자:', 280, 0), positioned('김가나', 380, 0)]
    candidates = build_paddle_candidate_hints_from_safe_lines(lines)
    assert [c['value'] for c in candidates if c['candidate_type'] == 'merchant_name'] == ['새봄공방']


@pytest.mark.parametrize('name', ['새봄:공방', 'Light: Workshop'])
def test_a_colon_inside_a_merchant_name_is_not_a_field_boundary(name):
    candidates = build_paddle_candidate_hints_from_safe_lines([positioned('상호: '+name, 0, 0, 220)])
    assert next(c['value'] for c in candidates if c['candidate_type'] == 'merchant_name') == name


def fragmented_payload():
    lines = [positioned('총합계', 0, 80), positioned('17', 200, 80), positioned('50', 275, 80)]
    return dict(lines=lines, key_value_candidates=build_paddle_candidate_hints_from_safe_lines(lines))


@pytest.mark.parametrize('reading,confidence,expected', [('17,500', .99, '17500'),
                                                        ('0', .99, '0'),
                                                        ('17,500', .8, None), ('17,50', .99, None)])
def test_fragmented_existing_total_is_rechecked_from_its_own_numeric_area(tmp_path, reading, confidence, expected):
    path = tmp_path/'synthetic.png'
    Image.new('RGB', (450, 200), 'white').save(path)
    class Engine:
        def ocr(self, crop, *, det, cls):
            assert not det and not cls
            assert crop.shape[1] > crop.shape[0]
            return [[(reading, confidence)]]
    result = PaddleOCRProvider()._reread_fragmented_total_rows(Engine(), path, fragmented_payload())
    if expected is not None:
        for kind in ['total_amount', 'final_amount']:
            candidate = next(c for c in result['key_value_candidates'] if c['candidate_type'] == kind)
            assert candidate['value'] == expected
            assert candidate['source_block_ids'][-1].startswith('total-row-')
    else:
        assert not any(c['value'] == '17500' for c in result['key_value_candidates'])


def test_valid_grouped_total_is_not_reread(tmp_path):
    path = tmp_path/'synthetic.png'
    Image.new('RGB', (450, 200), 'white').save(path)
    class Engine:
        def ocr(self, *args, **kwargs):
            pytest.fail('valid observed total must not add OCR calls')
    payload = fragmented_payload()
    payload['lines'][2]['text'] = '500'
    result = PaddleOCRProvider()._reread_fragmented_total_rows(Engine(), path, payload)
    assert result == payload


def test_reread_preserves_other_total_evidence_for_conflict_review(tmp_path):
    path = tmp_path/'synthetic.png'
    Image.new('RGB', (450, 200), 'white').save(path)
    payload = fragmented_payload()
    payload['key_value_candidates'].append(dict(key='total_amount', candidate_type='total_amount',
        value='28900', normalized_value='28900', source_block_ids=['other-total']))
    class Engine:
        def ocr(self, *args, **kwargs):
            return [[('17,500', .99)]]
    result = PaddleOCRProvider()._reread_fragmented_total_rows(Engine(), path, payload)
    assert {c['value'] for c in result['key_value_candidates'] if c['candidate_type']=='total_amount'} == {'17500','28900'}
    assert 'paddle_fragmented_total_reread' in result['warnings']
