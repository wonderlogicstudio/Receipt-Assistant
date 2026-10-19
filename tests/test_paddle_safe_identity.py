"""Synthetic identity preservation across the standard OCR boundary."""
import pytest

from app.ocr.paddle_provider import PaddleOCRProvider
from app.parser.receipt_parser import ReceiptParser
from app.parser.standard_ocr_context import build_parser_context_from_standard_ocr


def recognize(*texts):
    provider = PaddleOCRProvider()
    payload = provider._sanitize_result([{'text': text, 'confidence': .99} for text in texts])
    result = provider.adapter.convert(payload, source_file_name='synthetic.png')
    return result, ReceiptParser().parse_standard_context(build_parser_context_from_standard_ocr(result))


@pytest.mark.parametrize('contact', ['TEL:02-1234-5678', 'mail:sample@example.com'])
def test_redacted_contact_does_not_discard_same_line_business_or_merchant(contact):
    result, record = recognize('상호: 초록놀이 바다점 '+contact,
                               '사업자번호:123-45-67891 '+contact, '합계 17,530')
    assert record.merchant_name == '초록놀이 바다점'
    assert record.business_number == '123-45-67891'
    assert record.total_amount == 17530
    dumped = result.model_dump_json()
    assert '02-1234-5678' not in dumped and 'sample@example.com' not in dumped
    assert any(block.sensitive_category for block in result.text_blocks)


def test_credentials_are_not_recovered_as_identity():
    result, record = recognize('password 상호: 초록놀이', 'api key 사업자번호:123-45-67891')
    assert record.merchant_name is None and record.business_number is None
    assert all(block.text == '[REDACTED]' for block in result.text_blocks)


@pytest.mark.parametrize('title', ['영수증 ', '[영 수 증] ', '카드판매 영수증 '])
def test_title_merged_with_name_uses_observed_name_near_business_information(title):
    result, record = recognize(title+'초록놀이 바다점', '[고객용]',
                               '사업자번호:123-45-67891', '상호:', '합계 17,530')
    assert record.merchant_name == '초록놀이 바다점'
    assert record.business_number == '123-45-67891'
    assert any('영' in block.text for block in result.text_blocks)


def test_title_does_not_replace_an_empty_business_name_with_customer_copy():
    _, record = recognize('[영수증]', '[고객용]', '상호:', '사업자번호:123-45-67891')
    assert record.merchant_name is None


def test_missing_header_name_is_reread_near_business_anchor_with_restored_coordinates(tmp_path):
    from PIL import Image
    path = tmp_path/'synthetic.png'
    Image.new('RGB',(400,800),'white').save(path)
    provider = PaddleOCRProvider()
    def line(text,y):
        return [[[40,y],[280,y],[280,y+24],[40,y+24]],(text,.99)]
    source = provider._sanitize_result([line('영수증',200),line('사업자번호:123-45-67891',300)])
    class Engine:
        calls = 0
        def ocr(self,image,*,cls):
            assert not cls and image.shape[0] < 200
            self.calls += 1
            return [[line('초록놀이 바다점',10),line('사업자번호:123-45-67891',50)]]
    engine = Engine()
    result = provider._header_identity_result(engine,path,source)
    assert engine.calls == 1
    assert next(c['value'] for c in result['key_value_candidates'] if c['candidate_type']=='merchant_name') == '초록놀이 바다점'
    assert result['lines'][0]['bbox'][0][1] > 200


def test_missing_business_anchor_does_not_trigger_header_recognition(tmp_path):
    class Engine:
        def ocr(self,*args,**kwargs):
            pytest.fail('No positional identity anchor')
    assert PaddleOCRProvider()._header_identity_result(Engine(),tmp_path/'unused.png',{'lines':[]}) is None


@pytest.mark.parametrize('observed,accepted', [('바다점',False), ('상호: 바다점',True)])
def test_header_reread_requires_label_for_short_branch_fragment(tmp_path,observed,accepted):
    from PIL import Image
    path = tmp_path/'synthetic.png'
    Image.new('RGB',(400,800),'white').save(path)
    provider = PaddleOCRProvider()
    def line(text,y):
        return [[[40,y],[280,y],[280,y+24],[40,y+24]],(text,.99)]
    source = provider._sanitize_result([line('영수증',200),line('사업자번호:123-45-67891',300)])
    class Engine:
        def ocr(self,image,*,cls):
            return [[line(observed,10),line('사업자번호:123-45-67891',50)]]
    result = provider._header_identity_result(Engine(),path,source)
    assert any(c['candidate_type']=='merchant_name' for c in result['key_value_candidates']) is accepted
