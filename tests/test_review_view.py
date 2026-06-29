from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from app.core.config import AppConfig
from app.core.enums import CardMatchStatus, EvidenceType, ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.ui.review_view import _SessionCachedMerchantMatcher, _preview_image_payload, _selected_review_dataframe
from app.ui.settings_view import MERCHANT_CSV_MAX_UPLOAD_SIZE_BYTES, import_merchant_dictionary_uploaded_files
from app.ui.review_utils import (
    PREVIEW_KIND_BLOCKED,
    PREVIEW_KIND_IMAGE,
    PREVIEW_KIND_PDF,
    resolve_receipt_source_preview,
)


class FakeUploadedFile:
    def __init__(self, name: str, payload: bytes, size: int | None = None) -> None:
        self.name = name
        self._payload = payload
        self.size = len(payload) if size is None else size

    def getvalue(self) -> bytes:
        return self._payload


def make_receipt(*, stored_relative_path: str | None, source_file_name: str = "receipt.jpg") -> ReceiptRecord:
    return ReceiptRecord.create(
        session_id="session-1",
        source_file_id="source-file-1",
        ocr_result_id="ocr-result-1",
        source_file_name=source_file_name,
        stored_relative_path=stored_relative_path,
        evidence_type=EvidenceType.RECEIPT_IMAGE.value,
        transaction_date=date(2026, 6, 14),
        merchant_name="테스트상호",
        business_number="123-45-67890",
        total_amount=12000,
        supply_amount=None,
        vat_amount=None,
        payment_method="카드",
        expense_category="복리후생비",
        review_status=ReviewStatus.NEEDS_REVIEW.value,
        review_reason="",
        card_match_status=CardMatchStatus.MATCHED.value,
        confidence=0.9,
        parser_warnings=[],
    )


def test_source_preview_blocks_paths_outside_data_uploads(tmp_path: Path) -> None:
    upload_root = tmp_path / "data" / "uploads"
    outside = tmp_path / "outside" / "receipt.jpg"
    outside.parent.mkdir(parents=True)
    outside.write_bytes(b"not a real receipt")

    preview = resolve_receipt_source_preview(
        make_receipt(stored_relative_path="../outside/receipt.jpg"),
        upload_root=upload_root,
        upload_relative_root=Path("data/uploads"),
    )

    assert preview.kind == PREVIEW_KIND_BLOCKED
    assert preview.path is None
    assert "outside" not in preview.message


def test_source_preview_resolves_image_inside_upload_root(tmp_path: Path) -> None:
    upload_root = tmp_path / "data" / "uploads"
    image_path = upload_root / "session-1" / "receipt.jpg"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"synthetic image placeholder")

    preview = resolve_receipt_source_preview(
        make_receipt(
            stored_relative_path="data/uploads/session-1/receipt.jpg",
            source_file_name=r"C:\private\receipt.jpg",
        ),
        upload_root=upload_root,
        upload_relative_root=Path("data/uploads"),
    )

    assert preview.kind == PREVIEW_KIND_IMAGE
    assert preview.is_image
    assert preview.path == image_path.resolve(strict=False)
    assert preview.source_file_name == "receipt.jpg"
    assert "private" not in preview.source_file_name


def test_source_preview_returns_pdf_notice_without_rendering(tmp_path: Path) -> None:
    upload_root = tmp_path / "data" / "uploads"
    pdf_path = upload_root / "session-1" / "receipt.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF synthetic placeholder")

    preview = resolve_receipt_source_preview(
        make_receipt(
            stored_relative_path="data/uploads/session-1/receipt.pdf",
            source_file_name="receipt.pdf",
        ),
        upload_root=upload_root,
        upload_relative_root=Path("data/uploads"),
    )

    assert preview.kind == PREVIEW_KIND_PDF
    assert preview.is_pdf
    assert "PDF 원본 파일입니다" in preview.message
    assert preview.path == pdf_path.resolve(strict=False)


def test_merchant_dictionary_uploaded_files_imports_safe_summary_only(tmp_path: Path) -> None:
    payload = (
        "상호명,도로명,건물본번지,건물부번지,도로명주소,대표자명,전화번호\n"
        "테스트상점,종로,1,0,서울특별시 종로구 종로 1,홍길동,02-1234-5678\n"
    ).encode("utf-8-sig")
    config = AppConfig(app_db_path=tmp_path / "merchant.db")

    results = import_merchant_dictionary_uploaded_files(
        [FakeUploadedFile(r"C:\private\public_stores.csv", payload)],
        config=config,
    )

    serialized = str(results)

    assert results[0].source_file_name == "public_stores.csv"
    assert results[0].imported_row_count == 1
    assert "C:" not in serialized
    assert "private" not in serialized
    assert "홍길동" not in serialized
    assert "02-1234-5678" not in serialized


def test_merchant_dictionary_uploaded_files_rejects_files_over_400mb(tmp_path: Path) -> None:
    config = AppConfig(app_db_path=tmp_path / "merchant.db")

    with pytest.raises(ValueError, match="merchant_csv_upload_too_large"):
        import_merchant_dictionary_uploaded_files(
            [
                FakeUploadedFile(
                    r"C:\private\huge_public_stores.csv",
                    "상호명,도로명주소\n".encode("utf-8-sig"),
                    size=MERCHANT_CSV_MAX_UPLOAD_SIZE_BYTES + 1,
                )
            ],
            config=config,
        )


def test_session_cached_merchant_matcher_reuses_same_lookup() -> None:
    class FakeMatcher:
        def __init__(self) -> None:
            self.call_count = 0

        def find_candidates(self, *, merchant_name=None, business_number=None, address_hint=None):
            self.call_count += 1
            return [f"candidate-{self.call_count}"]

    fake = FakeMatcher()
    cache: dict[tuple[str, str, str], list[object]] = {}
    metrics: dict[str, object] = {}
    matcher = _SessionCachedMerchantMatcher(fake, cache, metrics)
    address_hint = {"road_name": "Jongno", "building_main_number": "19"}

    first = matcher.find_candidates(merchant_name="Store", business_number=None, address_hint=address_hint)
    second = matcher.find_candidates(merchant_name="Store", business_number=None, address_hint=address_hint)

    assert first == ["candidate-1"]
    assert second == ["candidate-1"]
    assert fake.call_count == 1
    assert metrics["candidate_lookup_count"] == 2
    assert metrics["candidate_cache_miss_count"] == 1
    assert metrics["candidate_cache_hit_count"] == 1
    assert "candidate_lookup_elapsed_ms" in metrics


def test_selected_review_dataframe_returns_only_selected_row() -> None:
    dataframe = pd.DataFrame(
        [
            {"__receipt_id": "r1", "file": "first.jpg"},
            {"__receipt_id": "r2", "file": "second.jpg"},
        ]
    )

    selected = _selected_review_dataframe(dataframe, "r2")

    assert len(selected) == 1
    assert selected.iloc[0]["file"] == "second.jpg"


def test_preview_image_payload_does_not_fallback_to_full_path(tmp_path: Path) -> None:
    not_an_image = tmp_path / "private" / "receipt.jpg"
    not_an_image.parent.mkdir(parents=True)
    not_an_image.write_bytes(b"not an image")

    payload = _preview_image_payload(not_an_image)

    assert payload == ""
    assert str(tmp_path) not in str(payload)
