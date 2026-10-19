"""Opt-in local OCR evaluation; visual references never enter recognition."""
from __future__ import annotations

import argparse
import contextlib
from datetime import date
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import sys
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ocr.paddle_provider import PaddleOCRProvider
from app.parser.receipt_parser import ReceiptParser
from app.parser.standard_ocr_context import build_parser_context_from_standard_ocr

FIELDS = {"merchant_name", "business_number", "transaction_date", "total_amount",
          "discount_amount", "supply_amount", "vat_amount", "payment_method"}
MONEY_FIELDS = {"total_amount", "discount_amount", "supply_amount", "vat_amount"}


def evaluate(reference_path: Path, sample_dir: Path, *, use_gpu: bool = False) -> dict:
    references = json.loads(reference_path.read_text(encoding="utf-8"))
    if not isinstance(references, list) or not references:
        raise ValueError("invalid_reference")
    samples = []
    seen_images = set()
    for reference in references:
        name = reference["file_name"]
        if not name or name != Path(name).name or "\\" in name or ":" in name:
            raise ValueError("invalid_reference")
        path = (sample_dir / name).resolve()
        if not path.is_relative_to(sample_dir.resolve()) or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            raise ValueError("invalid_reference")
        if sha256(path.read_bytes()).hexdigest() != reference["sha256"]:
            raise ValueError("reference_image_mismatch")
        if reference["sha256"] in seen_images:
            raise ValueError("duplicate_reference_image")
        seen_images.add(reference["sha256"])
        expected = reference["expected"]
        if not expected or not set(expected).issubset(FIELDS):
            raise ValueError("invalid_reference")
        for field, value in expected.items():
            valid_type = type(value) is int if field in MONEY_FIELDS else isinstance(value, str)
            if value is not None and not valid_type:
                raise ValueError("invalid_reference")
            if isinstance(value, str) and not any(char.isalnum() for char in value):
                raise ValueError("invalid_reference")
            if field == "business_number" and value is not None and not re.fullmatch(r"(?:\d{10}|\d{3}-\d{2}-\d{5})", value):
                raise ValueError("invalid_reference_business_number")
            if field == "transaction_date" and value is not None:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError("invalid_reference_date")
                date.fromisoformat(value)
        samples.append((path, expected))

    rows = []
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        provider = PaddleOCRProvider(use_gpu=use_gpu)
        for index, (path, expected) in enumerate(samples, 1):
            started = perf_counter()
            result = provider.extract(path, source_file_name="evaluation.jpg")
            record = ReceiptParser().parse_standard_context(build_parser_context_from_standard_ocr(result))
            fields = {}
            for field, wanted in expected.items():
                actual = getattr(record, field)
                if hasattr(actual, "isoformat"):
                    actual = actual.isoformat()
                if field == "merchant_name" and actual is not None and wanted is not None:
                    normalize = lambda value: re.sub(r"[^0-9A-Za-z가-힣]", "", value).lower()
                    matches = normalize(actual) == normalize(wanted)
                else:
                    matches = actual == wanted
                fields[field] = "match" if matches else ("missing" if actual is None else "different")
            rows.append({"sample_id": f"S{index:02}", "status": result.status,
                         "seconds": round(perf_counter() - started, 2), "fields": fields})
    scored = sum(len(row["fields"]) for row in rows)
    matched = sum(value == "match" for row in rows for value in row["fields"].values())
    nonempty = [(row["fields"][field], wanted) for row, (_, expected) in zip(rows, samples)
                for field, wanted in expected.items() if wanted is not None]
    return {"sample_count": len(rows), "scored_fields": scored, "matched_fields": matched,
            "nonempty_reference_fields": len(nonempty),
            "matched_nonempty_fields": sum(status == "match" for status, _ in nonempty),
            "ocr_completed": sum(row["status"] == "completed" for row in rows), "samples": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--sample-dir", type=Path, default=Path("samples/receipts"))
    parser.add_argument("--output", type=Path, default=Path("output/quality_runs/local_evaluation.json"))
    parser.add_argument("--gpu", action="store_true")
    args = parser.parse_args()
    try:
        report = evaluate(args.reference, args.sample_dir, use_gpu=args.gpu)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except Exception:
        print("evaluation_failed: check local references, image hashes, and OCR environment")
        return 2
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}))
    return int(report["matched_fields"] != report["scored_fields"] or report["ocr_completed"] != report["sample_count"])


if __name__ == "__main__":
    raise SystemExit(main())
