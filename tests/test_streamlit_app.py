from datetime import datetime

from app.ocr.mock_provider import MockOCRProvider
from app.ocr.adapters.paddle_standard_adapter import PaddleStandardOCRAdapter
from app.ocr.paddle_provider import build_paddle_candidate_hints_from_safe_lines
from app.ocr.provider_factory import get_ocr_provider
from app.parser.receipt_parser import ReceiptParser
from app.storage.file_store import StoredFileMetadata
from app.core.ocr_models import OCRResult
from app.core.standard_ocr import StandardOCRKeyValueCandidate, StandardOCRResult, StandardOCRTextBlock
from app.ui.streamlit_app import (
    PREVIEW_COLUMNS,
    build_paddle_gpu_diagnostic_rows,
    build_runtime_ocr_config,
    format_ocr_diagnostic,
    is_paddle_runtime_provider,
    process_receipt_files_with_mock_ocr,
    receipts_to_preview_dataframe,
    resolve_runtime_ocr_provider_name,
    should_disable_process_button,
    stored_files_to_dataframe,
)


def test_receipts_to_preview_dataframe_hides_raw_ocr_fields(tmp_path):
    receipt_path = tmp_path / "sample_receipt.jpg"
    receipt_path.write_bytes(b"sample")
    receipt = ReceiptParser().parse(MockOCRProvider().extract(receipt_path))

    dataframe = receipts_to_preview_dataframe([receipt])

    assert list(dataframe.columns) == PREVIEW_COLUMNS
    assert "ocr_raw_text" not in dataframe.columns
    assert "raw_json" not in dataframe.columns
    assert dataframe.loc[0, "merchant_name"] == "샘플문구 강남점"


def test_stored_files_to_dataframe_hides_original_path_parts():
    metadata = StoredFileMetadata(
        original_file_name=r"C:\private\receipt.pdf",
        stored_file_name="receipt_abc.pdf",
        stored_relative_path="data/uploads/session/receipt_abc.pdf",
        file_extension=".pdf",
        file_size_bytes=10,
        session_id="session",
    )

    dataframe = stored_files_to_dataframe([metadata])

    assert dataframe.loc[0, "original_file_name"] == "receipt.pdf"
    assert "C:" not in dataframe.loc[0, "original_file_name"]


def test_format_ocr_diagnostic_uses_safe_tokens_only():
    result = OCRResult.failed(
        source_file_id="id",
        source_file_name="receipt.jpg",
        stored_relative_path=r"C:\private\receipt.jpg",
        provider="azure",
        error_message="do not show this",
        diagnostic_code="proxy_error",
    )

    diagnostic = format_ocr_diagnostic(result)

    assert diagnostic == "status=failed, provider=azure, reason=proxy_error"
    assert "receipt.jpg" not in diagnostic
    assert "private" not in diagnostic
    assert "do not show this" not in diagnostic


def test_should_disable_process_button_when_empty_or_processing():
    assert should_disable_process_button([], is_processing=False) is True
    assert should_disable_process_button(None, is_processing=False) is True
    assert should_disable_process_button([object()], is_processing=True) is True
    assert should_disable_process_button([object()], is_processing=False) is False
    assert should_disable_process_button([object()], is_processing=False, runtime_blocked=True) is True


def test_runtime_ocr_provider_selection_resolves_current_or_safe_override(monkeypatch):
    assert resolve_runtime_ocr_provider_name("__current__", "azure") == "azure"
    assert resolve_runtime_ocr_provider_name("mock", "azure") == "mock"
    assert resolve_runtime_ocr_provider_name("azure", "mock") == "azure"
    assert resolve_runtime_ocr_provider_name("paddle", "azure") == "paddle"
    assert resolve_runtime_ocr_provider_name("paddleocr", "azure") == "paddleocr"
    assert resolve_runtime_ocr_provider_name("unknown", "azure") == "azure"

    monkeypatch.setenv("OCR_PROVIDER", "azure")
    config = build_runtime_ocr_config("mock")

    assert config.ocr_provider == "mock"


def test_paddle_gpu_option_is_only_for_paddle_provider():
    assert is_paddle_runtime_provider("paddle") is True
    assert is_paddle_runtime_provider("paddleocr") is True
    assert is_paddle_runtime_provider("mock") is False
    assert is_paddle_runtime_provider("azure") is False
    assert is_paddle_runtime_provider(None) is False


def test_runtime_paddle_gpu_default_config_stays_cpu(monkeypatch):
    monkeypatch.setenv("OCR_PROVIDER", "mock")
    monkeypatch.delenv("PADDLE_USE_GPU", raising=False)

    config = build_runtime_ocr_config("paddle")

    assert config.ocr_provider == "paddle"
    assert config.paddle_use_gpu is False


def test_runtime_paddle_gpu_true_is_passed_to_provider(monkeypatch):
    monkeypatch.setenv("OCR_PROVIDER", "mock")

    config = build_runtime_ocr_config("paddle", paddle_use_gpu=True)
    provider = get_ocr_provider(config)

    assert config.ocr_provider == "paddle"
    assert config.paddle_use_gpu is True
    assert getattr(provider, "use_gpu") is True


def test_runtime_paddle_gpu_false_is_passed_to_provider(monkeypatch):
    monkeypatch.setenv("OCR_PROVIDER", "mock")
    monkeypatch.setenv("PADDLE_USE_GPU", "true")

    config = build_runtime_ocr_config("paddle", paddle_use_gpu=False)
    provider = get_ocr_provider(config)

    assert config.ocr_provider == "paddle"
    assert config.paddle_use_gpu is False
    assert getattr(provider, "use_gpu") is False


def test_runtime_paddle_gpu_override_does_not_affect_non_paddle_provider(monkeypatch):
    monkeypatch.setenv("OCR_PROVIDER", "mock")

    config = build_runtime_ocr_config("azure", paddle_use_gpu=True)

    assert config.ocr_provider == "azure"
    assert config.paddle_use_gpu is False


def test_paddle_gpu_diagnostic_rows_are_safe():
    rows = build_paddle_gpu_diagnostic_rows(
        {
            "cuda_compiled": False,
            "device": r"C:\private\receipt.jpg",
            "diagnostic_code": "hidden",
        },
        gpu_requested=True,
    )
    rendered = " ".join(f"{label}={value}" for label, value in rows)

    assert rows == [
        ("gpu_requested", True),
        ("cuda_compiled", False),
        ("device", "c_private_receipt_jpg"),
    ]
    assert "raw_text" not in rendered
    assert "raw_json" not in rendered
    assert "traceback" not in rendered
    assert "C:\\" not in rendered
    assert "private\\receipt" not in rendered


def test_process_receipt_files_accepts_standard_ocr_provider_result():
    metadata = StoredFileMetadata(
        original_file_name=r"C:\private\paddle_receipt.jpg",
        stored_file_name="paddle_receipt.jpg",
        stored_relative_path="data/uploads/session/paddle_receipt.jpg",
        file_extension=".jpg",
        file_size_bytes=10,
        session_id="session",
    )

    result = process_receipt_files_with_mock_ocr(
        [metadata],
        ocr_provider=FakeStandardOCRProvider(),
    )

    assert not result.errors
    assert len(result.receipt_records) == 1
    receipt = result.receipt_records[0]
    assert receipt.ocr_provider == "paddleocr"
    assert receipt.source_file_name == "paddle_receipt.jpg"
    assert receipt.stored_relative_path == "data/uploads/session/paddle_receipt.jpg"
    assert receipt.merchant_name == "테스트카페"
    assert receipt.transaction_date and receipt.transaction_date.isoformat() == "2026-06-10"
    assert receipt.total_amount == 12000
    assert "private" not in receipt.source_file_name
    assert isinstance(result.ocr_results[0], StandardOCRResult)


def test_process_receipt_files_keeps_address_hint_as_transient_matching_data():
    metadata = StoredFileMetadata(
        original_file_name=r"C:\private\address_receipt.jpg",
        stored_file_name="address_receipt.jpg",
        stored_relative_path="data/uploads/session/address_receipt.jpg",
        file_extension=".jpg",
        file_size_bytes=10,
        session_id="session",
    )

    result = process_receipt_files_with_mock_ocr(
        [metadata],
        ocr_provider=FakeTextOnlyStandardProvider(
            [
                "상호명 테스트상점",
                "주소 서울특별시 서대문구 이화여대길 52-31",
                "합계금액 12,000",
            ]
        ),
    )

    receipt = result.receipt_records[0]
    hint = result.merchant_address_hints[receipt.id]
    serialized_receipt = str(receipt.to_dict())

    assert hint["road_name"] == "이화여대길"
    assert hint["building_main_number"] == "52"
    assert hint["building_sub_number"] == "31"
    assert "이화여대길" not in serialized_receipt
    assert "C:" not in str(result.merchant_address_hints)
    assert "private" not in str(result.merchant_address_hints)


def test_process_receipt_files_preserves_observed_name_without_dictionary_cleanup():
    metadata = StoredFileMetadata(
        original_file_name="playworld.jpg",
        stored_file_name="playworld.jpg",
        stored_relative_path="data/uploads/session/playworld.jpg",
        file_extension=".jpg",
        file_size_bytes=10,
        session_id="session",
    )

    result = process_receipt_files_with_mock_ocr(
        [metadata],
        ocr_provider=FakePaddleLineProvider(
            [
                "상호명 어스즈 플레이월드 파주점 STO",
                "사업자번호: 503-33-22495",
                "출력일시 : 2026-06-06 11:01:24",
                "합계금액 61,000",
            ]
        ),
    )

    assert not result.errors
    receipt = result.receipt_records[0]
    assert receipt.merchant_name == "어스즈 플레이월드 파주점 STO"
    assert receipt.business_number == "503-33-22495"
    assert receipt.transaction_date and receipt.transaction_date.isoformat() == "2026-06-06"
    assert receipt.total_amount == 61000


def test_process_receipt_files_preserves_observed_name_without_candidates():
    metadata = StoredFileMetadata(
        original_file_name="playworld_no_candidates.jpg",
        stored_file_name="playworld_no_candidates.jpg",
        stored_relative_path="data/uploads/session/playworld_no_candidates.jpg",
        file_extension=".jpg",
        file_size_bytes=10,
        session_id="session",
    )

    result = process_receipt_files_with_mock_ocr(
        [metadata],
        ocr_provider=FakeTextOnlyStandardProvider(
            [
                "상호명 어스즈 플레이월드 파주점 STO",
                "출력일시 : 2026-06-06 11:01:24",
                "합계금액 61,000",
            ]
        ),
    )

    assert not result.errors
    receipt = result.receipt_records[0]
    assert receipt.merchant_name == "어스즈 플레이월드 파주점 STO"
    assert receipt.transaction_date and receipt.transaction_date.isoformat() == "2026-06-06"
    assert receipt.total_amount == 61000


def test_process_receipt_files_applies_owner_line_merchant_and_compact_datetime():
    metadata = StoredFileMetadata(
        original_file_name="kimbap.jpg",
        stored_file_name="kimbap.jpg",
        stored_relative_path="data/uploads/session/kimbap.jpg",
        file_extension=".jpg",
        file_size_bytes=10,
        session_id="session",
    )

    result = process_receipt_files_with_mock_ocr(
        [metadata],
        ocr_provider=FakePaddleLineProvider(
            [
                "총각김밥 / 152-21-01299 / 박준이",
                "승인일시",
                "20260526125309",
                "합계 5,600",
            ]
        ),
    )

    assert not result.errors
    receipt = result.receipt_records[0]
    assert receipt.merchant_name == "총각김밥"
    assert receipt.business_number == "152-21-01299"
    assert receipt.transaction_date and receipt.transaction_date.isoformat() == "2026-05-26"
    assert receipt.total_amount == 5600


def test_process_receipt_files_applies_split_owner_line_merchant_and_split_datetime():
    metadata = StoredFileMetadata(
        original_file_name="kimbap_split.jpg",
        stored_file_name="kimbap_split.jpg",
        stored_relative_path="data/uploads/session/kimbap_split.jpg",
        file_extension=".jpg",
        file_size_bytes=10,
        session_id="session",
    )

    result = process_receipt_files_with_mock_ocr(
        [metadata],
        ocr_provider=FakePaddleLineProvider(
            [
                "총각김밥 /",
                "152-21-01299 / 박준이",
                "승인일시 :",
                "20260526",
                "12:53:09",
                "합계 5,600",
            ]
        ),
    )

    assert not result.errors
    receipt = result.receipt_records[0]
    assert receipt.merchant_name == "총각김밥"
    assert receipt.business_number == "152-21-01299"
    assert receipt.transaction_date and receipt.transaction_date.isoformat() == "2026-05-26"
    assert receipt.total_amount == 5600


def test_process_receipt_files_keeps_livestock_distribution_merchant_and_approval_number():
    metadata = StoredFileMetadata(
        original_file_name="livestock.jpg",
        stored_file_name="livestock.jpg",
        stored_relative_path="data/uploads/session/livestock.jpg",
        file_extension=".jpg",
        file_size_bytes=10,
        session_id="session",
    )

    result = process_receipt_files_with_mock_ocr(
        [metadata],
        ocr_provider=FakePaddleLineProvider(
            [
                "정선축산유통",
                "사업자번호 206-85-10228",
                "승인일시 20260526152446",
                "승인번호 73297759",
                "합계 107,000",
            ]
        ),
    )

    assert not result.errors
    receipt = result.receipt_records[0]
    assert receipt.merchant_name == "정선축산유통"
    assert receipt.transaction_date and receipt.transaction_date.isoformat() == "2026-05-26"
    assert receipt.approval_number == "73297759"
    assert receipt.total_amount == 107000


def test_process_receipt_files_preserves_observed_hotel_name_without_inventing_tax_total():
    metadata = StoredFileMetadata(
        original_file_name="hotel_split_tax.jpg",
        stored_file_name="hotel_split_tax.jpg",
        stored_relative_path="data/uploads/session/hotel_split_tax.jpg",
        file_extension=".jpg",
        file_size_bytes=10,
        session_id="session",
    )

    result = process_receipt_files_with_mock_ocr(
        [metadata],
        ocr_provider=FakePaddleLineProvider(
            [
                "상호 : 한화호텔앤드리조트(주) / 설악",
                "사업자 : 101-81-30747",
                "승",
                "인",
                "간",
                "N9260525085745208437",
                "비씨카드",
                "272원",
                "657",
                "728원",
                "65",
                "72300원",
            ]
        ),
    )

    assert not result.errors
    receipt = result.receipt_records[0]
    assert receipt.merchant_name == "한화호텔앤드리조트(주) / 설악"
    assert receipt.transaction_date and receipt.transaction_date.isoformat() == "2026-05-25"
    assert receipt.business_number == "101-81-30747"
    assert receipt.total_amount != 723000
    assert receipt.supply_amount is None
    assert receipt.vat_amount is None


class FakeStandardOCRProvider:
    provider_name = "paddleocr"

    def extract(self, _source: object) -> StandardOCRResult:
        return StandardOCRResult(
            id="standard-test",
            provider="paddleocr",
            provider_version="test",
            engine_runtime="pc_local",
            status="completed",
            text_blocks=[
                StandardOCRTextBlock(
                    page_index=0,
                    block_id="line-1",
                    text="상호명 테스트카페",
                    normalized_text="상호명 테스트카페",
                    confidence=0.98,
                    line_order=0,
                )
            ],
            key_value_candidates=[
                StandardOCRKeyValueCandidate(
                    key="merchant_name",
                    candidate_type="merchant_name",
                    value="테스트카페",
                    normalized_value="테스트카페",
                ),
                StandardOCRKeyValueCandidate(
                    key="transaction_date",
                    candidate_type="transaction_date",
                    value="2026-06-10",
                    normalized_value="2026-06-10",
                ),
                StandardOCRKeyValueCandidate(
                    key="total_amount",
                    candidate_type="total_amount",
                    value="12,000",
                    normalized_value="12000",
                ),
                StandardOCRKeyValueCandidate(
                    key="payment_method",
                    candidate_type="payment_method",
                    value="카드",
                    normalized_value="카드",
                ),
            ],
            confidence=0.98,
            created_at=datetime(2026, 6, 10, 12, 0, 0),
        )


class FakePaddleLineProvider:
    provider_name = "paddleocr"

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines

    def extract(self, _source: object) -> StandardOCRResult:
        text_blocks = [
            {
                "block_id": f"line-{index}",
                "page_index": 0,
                "line_order": index,
                "text": text,
                "normalized_text": text,
                "confidence": 0.98,
                "block_type": "line",
            }
            for index, text in enumerate(self.lines)
        ]
        return PaddleStandardOCRAdapter().convert(
            {
                "engine": "paddleocr",
                "engine_version": "test",
                "status": "succeeded",
                "language_hint": "ko",
                "input_type": "image",
                "image_count": 1,
                "pages": [{"page_index": 0, "unit": "synthetic"}],
                "lines": text_blocks,
                "key_value_candidates": build_paddle_candidate_hints_from_safe_lines(text_blocks),
            },
            source_file_id="fake-paddle-lines",
            source_file_name="fake.jpg",
            provider_version="test",
        )


class FakeTextOnlyStandardProvider:
    provider_name = "paddleocr"

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines

    def extract(self, _source: object) -> StandardOCRResult:
        return StandardOCRResult(
            id="text-only-standard-test",
            provider="paddleocr",
            provider_version="test",
            engine_runtime="pc_local",
            status="completed",
            text_blocks=[
                StandardOCRTextBlock(
                    page_index=0,
                    block_id=f"text-only-line-{index}",
                    text=text,
                    normalized_text=text,
                    confidence=0.98,
                    line_order=index,
                )
                for index, text in enumerate(self.lines)
            ],
            key_value_candidates=[],
            confidence=0.98,
            created_at=datetime(2026, 6, 10, 12, 0, 0),
        )
