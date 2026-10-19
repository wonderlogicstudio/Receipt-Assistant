import pytest
from PIL import Image

from app.ocr import paddle_provider as module


def payload(label, amount, *, kind='total_amount'):
    return dict(lines=[dict(block_id='label', text=label, confidence=.99)],
                key_value_candidates=[dict(key=kind, candidate_type=kind, value=amount,
                    normalized_value=amount, confidence=.99, source_block_ids=['label'])])


def test_stronger_total_replaces_a_filled_weak_transaction_amount():
    merged = module._merge_missing_candidate_hints(payload('거래금액', '15918'),
        payload('총합계', '17510'), allowed_types={'total_amount'})
    assert [c['value'] for c in merged['key_value_candidates']] == ['17510']
    assert merged['key_value_candidates'][0]['source_block_ids'][0].startswith('supplemental-')


def test_weaker_or_invalid_supplement_cannot_remove_a_valid_total():
    for label,value in [('거래금액','15918'),('총합계',''),('총합계','[REDACTED]')]:
        merged = module._merge_missing_candidate_hints(payload('합계','17510'),
            payload(label,value), allowed_types={'total_amount'})
        assert [c['value'] for c in merged['key_value_candidates']] == ['17510']


@pytest.mark.parametrize('readings,expected', [
    ([('17,510',.99),('17,510',.99)], '17510'),
    ([('0',.99),('0',.99)], '0'),
    ([('17,510',.96),('17,510',.99)], '15918'),
    ([('17,510',.99),('17,610',.99)], '15918'),
])
def test_weak_filled_total_is_reread_only_from_its_explicit_total_row(tmp_path, monkeypatch, readings, expected):
    import numpy as np
    path = tmp_path/'synthetic.png'
    Image.new('RGB',(200,160),'white').save(path)
    source = payload('거래금액','15918')
    source['lines'].append(dict(block_id='total-label',text='총합계',confidence=.99))
    def whole_row(image,line,*,join_groups):
        assert join_groups
        return [(np.zeros((20,80,3),dtype='uint8'),[[0,0],[80,0],[80,20],[0,20]])]
    monkeypatch.setattr(module,'_numeric_row_crops',whole_row)
    class Engine:
        calls = 0
        def ocr(self, image, *, det, cls):
            assert not det and not cls
            reading = readings[self.calls]
            self.calls += 1
            return [[reading]]
    engine = Engine()
    result = module.PaddleOCRProvider()._reread_weak_total_row(engine,path,source)
    assert engine.calls == 2
    assert next(c['value'] for c in result['key_value_candidates'] if c['candidate_type']=='total_amount') == expected


@pytest.mark.parametrize('label', ['총합계', '영수금액', '결제금액', '신용카드'])
def test_strong_existing_total_does_not_add_recognition_calls(tmp_path,label):
    class Engine:
        def ocr(self,*args,**kwargs):
            pytest.fail('Do not reread a strongly anchored existing total')
    source = payload(label,'17510')
    assert module.PaddleOCRProvider()._reread_weak_total_row(Engine(),tmp_path/'unused.png',source) == source
