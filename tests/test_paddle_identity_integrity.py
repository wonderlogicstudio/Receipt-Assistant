import pytest

from app.ocr.paddle_provider import build_paddle_candidate_hints_from_safe_lines
from app.ocr.paddle_provider import _labeled_merchant_value


@pytest.mark.parametrize("name", ["크린에이드 새빛점", "현대오일뱅크 바다점", "대홍365약국", "무교삼계탕", "Independent Shop"])
def test_labeled_observed_name_is_not_rewritten(name):
    candidates = build_paddle_candidate_hints_from_safe_lines([
        {"block_id": "name", "text": f"상호명: {name}", "confidence": 0.99},
        {"block_id": "business", "text": "사업자등록번호: 206-86-50913", "confidence": 0.99},
    ])
    values = {c["candidate_type"]: c["value"] for c in candidates}
    assert values["merchant_name"] == name


def test_business_number_alone_does_not_create_merchant_candidate():
    candidates = build_paddle_candidate_hints_from_safe_lines([
        {"block_id": "business", "text": "사업자등록번호: 206-86-50913", "confidence": 0.99},
    ])
    assert not any(c["candidate_type"] == "merchant_name" for c in candidates)


def test_observed_branch_near_bottom_is_not_lost_due_to_header_cutoff():
    lines = [{"block_id": str(i), "text": "상품명 수량 단가", "confidence": 0.99} for i in range(50)]
    lines.append({"block_id": "branch", "text": "새빛문구 바다점", "confidence": 0.99})
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines(lines)}
    assert values["merchant_name"] == "새빛문구 바다점"


def test_digit_noise_inside_merchant_label_does_not_become_part_of_name():
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines([
        {"block_id": "name", "text": "가1맹 점 명: 새빛24(바다점)", "confidence": 0.99},
        {"block_id": "business", "text": "사업자번호 123-45-67891", "confidence": 0.99}])}
    assert values["merchant_name"] == "새빛24(바다점)"


def test_noisy_label_requires_separator_before_removing_observed_text():
    assert _labeled_merchant_value("가1맹점명카페") is None
