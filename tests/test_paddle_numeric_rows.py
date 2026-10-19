import pytest
from PIL import Image
from app.ocr.paddle_provider import PaddleOCRProvider


@pytest.mark.parametrize('reading,confidence,expected', [('0',.99,'0'),('17',.99,'17'),('0',.96,None),('그',.99,None)])
def test_numeric_reread_requires_printed_label_and_confident_numeric_evidence(tmp_path, monkeypatch, reading, confidence, expected):
    path=tmp_path/'synthetic.png'; Image.new('RGB',(300,200),'white').save(path)
    bbox=[[180,40],[200,40],[200,60],[180,60]]
    monkeypatch.setattr('app.ocr.paddle_provider._numeric_row_crops',lambda image,line:[(object(),bbox)])
    class Engine:
        def ocr(self,crop,det,cls):
            assert det is False and cls is False
            return [[(reading,confidence)]]
    payload={'lines':[dict(block_id='label',text='부가세',line_order=0)],'key_value_candidates':[]}
    result=PaddleOCRProvider()._read_missing_numeric_rows(Engine(),path,payload)
    if expected is None:
        assert not result['key_value_candidates']
    else:
        candidate=result['key_value_candidates'][0]
        assert candidate['value']==expected
        assert candidate['source_block_ids']==['label','numeric-row-1']
        assert result['lines'][-1]['bbox']==bbox


def test_numeric_reread_does_not_replace_existing_value_or_assign_unlabeled_number(tmp_path, monkeypatch):
    path=tmp_path/'synthetic.png';Image.new('RGB',(300,200),'white').save(path)
    def forbidden(*args):pytest.fail('existing or unlabeled values must not be reread')
    monkeypatch.setattr('app.ocr.paddle_provider._numeric_row_crops',forbidden)
    payload={'lines':[dict(block_id='a',text='부가세'),dict(block_id='b',text='1234')],
             'key_value_candidates':[dict(candidate_type='vat_amount',value='23')]}
    assert PaddleOCRProvider()._read_missing_numeric_rows(object(),path,payload)==payload


@pytest.mark.parametrize('label,kind', [('[부가세 과세물품가액]', 'supply_amount'),
                                       ('부 가 세(VAT):', 'vat_amount')])
def test_decorated_tax_labels_allow_observed_zero_reread(tmp_path, monkeypatch, label, kind):
    path = tmp_path/'synthetic.png'
    Image.new('RGB', (300, 200), 'white').save(path)
    bbox = [[180,40],[200,40],[200,60],[180,60]]
    monkeypatch.setattr('app.ocr.paddle_provider._numeric_row_crops', lambda image,line: [(object(),bbox)])
    class Engine:
        def ocr(self, *args, **kwargs):
            return [[('0', .99)]]
    result = PaddleOCRProvider()._read_missing_numeric_rows(Engine(), path,
        {'lines': [dict(block_id='label', text=label)], 'key_value_candidates': []})
    assert result['key_value_candidates'][0]['candidate_type'] == kind
    assert result['key_value_candidates'][0]['value'] == '0'


def test_numeric_reread_is_bounded_and_rejects_conflicting_crops(tmp_path, monkeypatch):
    path=tmp_path/'synthetic.png';Image.new('RGB',(300,200),'white').save(path)
    counts=[]
    def crops(image,line):
        counts.append(1)
        return [(1,[[0,0],[1,0],[1,1],[0,1]]),(2,[[0,0],[1,0],[1,1],[0,1]])]
    monkeypatch.setattr('app.ocr.paddle_provider._numeric_row_crops',crops)
    class Engine:
        def ocr(self,crop,**kwargs):return [[(str(crop),.99)]]
    payload={'lines':[dict(block_id=str(i),text='부가세') for i in range(10)],'key_value_candidates':[]}
    result=PaddleOCRProvider()._read_missing_numeric_rows(Engine(),path,payload)
    assert len(counts)==6
    assert not result['key_value_candidates']


def test_numeric_reread_compares_separate_labeled_rows_before_choosing(tmp_path, monkeypatch):
    path=tmp_path/'synthetic.png';Image.new('RGB',(300,200),'white').save(path)
    monkeypatch.setattr('app.ocr.paddle_provider._numeric_row_crops',
                        lambda image,line:[(line['block_id'],[[0,0],[1,0],[1,1],[0,1]])])
    class Engine:
        def ocr(self,crop,**kwargs):return [[(crop,.99)]]
    payload={'lines':[dict(block_id='17',text='부가세'),dict(block_id='28',text='부가세')],
             'key_value_candidates':[]}
    result=PaddleOCRProvider()._read_missing_numeric_rows(Engine(),path,payload)
    assert not result['key_value_candidates']
    assert 'numeric_row_conflict:vat_amount' in result['warnings']


def test_numeric_crop_stays_on_label_row():
    pytest.importorskip('cv2')
    from PIL import ImageDraw,ImageFont
    from app.ocr.paddle_provider import _numeric_row_crops
    image=Image.new('RGB',(400,200),'white')
    draw=ImageDraw.Draw(image);font=ImageFont.load_default(size=36)
    draw.text((280,40),'0',font=font,fill='black');draw.text((280,120),'999',font=font,fill='black')
    crops=_numeric_row_crops(image,dict(bbox=[[0,40],[140,40],[140,85],[0,85]]))
    assert crops
    assert all(max(y for x,y in bbox)<100 for crop,bbox in crops)
