from __future__ import annotations

from datetime import date
from pathlib import Path

from app.core.enums import CardMatchStatus, EvidenceType, ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.ui.review_utils import (
    PREVIEW_KIND_BLOCKED,
    PREVIEW_KIND_IMAGE,
    PREVIEW_KIND_PDF,
    resolve_receipt_source_preview,
)


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
