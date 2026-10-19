from PIL import Image
import pytest

from app.ocr.paddle_provider import PaddleOCRProvider, _should_try_orientation_fallback


@pytest.mark.parametrize("orientation", [1, 3, 6, 8])
def test_ocr_receives_pixels_with_phone_orientation_applied(tmp_path, orientation):
    image = Image.new("RGB", (80, 40), "white")
    image.paste("red", (0, 0, 40, 40))
    exif = image.getexif()
    exif[274] = orientation
    path = tmp_path / "phone.jpg"
    image.save(path, exif=exif)

    class InspectEngine:
        def ocr(self, filename, **kwargs):
            with Image.open(filename) as received:
                return received.size, received.getexif().get(274, 1), received.getpixel((5, 5))[1]

    size, tag, green = PaddleOCRProvider()._run_ocr(InspectEngine(), path, use_textline_orientation=False)
    assert size == ((40, 80) if orientation in {6, 8} else (80, 40))
    assert tag == 1
    assert (green < 30) is (orientation in {1, 6})


def test_amount_or_payment_word_alone_does_not_block_rotation_recovery():
    payload = {"key_value_candidates": [{"candidate_type": key} for key in ("total_amount", "payment_method")]}
    assert _should_try_orientation_fallback(payload)
    payload["key_value_candidates"].append({"candidate_type": "merchant_name"})
    assert not _should_try_orientation_fallback(payload)


@pytest.mark.parametrize('angle,box', [
    (0, [[20,30],[60,30],[60,50],[20,50]]),
    (90, [[30,40],[50,40],[50,80],[30,80]]),
    (180, [[40,150],[80,150],[80,170],[40,170]]),
    (270, [[150,20],[170,20],[170,60],[150,60]]),
])
def test_supplemental_rotation_restores_upright_coordinates_without_changing_values(angle, box):
    from app.ocr.paddle_provider import _restore_image_coordinates
    payload = {'lines': [dict(block_id='value', text='17,500', bbox=box)],
               'key_value_candidates': [dict(candidate_type='total_amount', value='17500', source_block_ids=['value'])]}
    restored = _restore_image_coordinates(payload, (100,200), angle)
    assert restored['lines'][0]['bbox'] == [[20,30],[60,30],[60,50],[20,50]]
    assert restored['key_value_candidates'] == payload['key_value_candidates']
    assert payload['lines'][0]['bbox'] == box


def test_enlarged_detail_crop_restores_offset_scale_and_rotation():
    from app.ocr.paddle_provider import _restore_image_coordinates
    payload = {'lines': [dict(block_id='value', text='17,500', bbox=[[0,0],[60,0],[60,120],[0,120]])]}
    restored = _restore_image_coordinates(payload, (100,200), 90, origin=(30,40), scale=3)
    assert restored['lines'][0]['bbox'] == [[20,30],[60,30],[60,50],[20,50]]
