from __future__ import annotations

from enum import Enum


class OCRStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class OCRProviderName(str, Enum):
    MOCK = "mock"


class CardParseStatus(str, Enum):
    PARSED = "parsed"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class CardParseResultStatus(str, Enum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class EvidenceType(str, Enum):
    RECEIPT_IMAGE = "receipt_image"
    RECEIPT_PDF = "receipt_pdf"
    OCR_TEXT = "ocr_text"
    MANUAL = "manual"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXCLUDED = "excluded"


class CardMatchStatus(str, Enum):
    UNMATCHED = "unmatched"
    MATCHED = "matched"
    CANDIDATE = "candidate"
    MISMATCH = "mismatch"
    NEEDS_REVIEW = "needs_review"
