from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ocr.azure_provider import AzureDocumentIntelligenceProvider
from app.ocr.paddle_provider import PaddleOCRProvider
from app.ui.ocr_comparison_report_utils import (
    build_side_by_side_report,
    build_standard_ocr_from_safe_azure_ocr_result,
)


CORE_FIELDS = {
    "merchant_name",
    "transaction_date",
    "business_number",
    "total_amount",
    "final_amount",
    "paid_amount",
    "supply_amount",
    "vat_amount",
    "payment_method",
    "approval_number",
    "review_status",
}


def main() -> int:
    args = parse_args()
    sample_paths = sorted(
        path
        for path in args.sample_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    selected_paths = sample_paths[args.start : args.start + args.limit]
    if not selected_paths:
        print("No sample files selected.")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output_dir / f"ocr_quality_anchor_{run_id}.json"

    azure_provider = AzureDocumentIntelligenceProvider()
    paddle_provider = PaddleOCRProvider()
    results: list[dict[str, Any]] = []

    print(f"Selected {len(selected_paths)} sample(s). Azure will be called once per sample.")
    for index, sample_path in enumerate(selected_paths, start=args.start):
        print(f"[{index}] {sample_path.name}")
        azure_standard, azure_elapsed_ms = run_azure(azure_provider, sample_path)
        paddle_standard, paddle_elapsed_ms = run_paddle(paddle_provider, sample_path)
        report = build_side_by_side_report(
            sample_id=sample_path.stem,
            source_file_name=sample_path.name,
            azure_result=azure_standard,
            paddle_result=paddle_standard,
            azure_elapsed_ms=azure_elapsed_ms,
            paddle_elapsed_ms=paddle_elapsed_ms,
        )
        safe_report = report.as_safe_dict()
        core_rows = [
            row
            for row in safe_report["field_rows"]
            if row["field_name"] in CORE_FIELDS
        ]
        item = {
            "sample_id": safe_report["sample_id"],
            "source_file_name": safe_report["source_file_name"],
            "summary_rows": safe_report["summary_rows"],
            "match_summary": safe_report["match_summary"],
            "core_field_rows": core_rows,
        }
        results.append(item)
        print_summary(item)

    payload = {
        "run_id": run_id,
        "sample_dir_name": args.sample_dir.name,
        "start": args.start,
        "limit": args.limit,
        "result_count": len(results),
        "results": results,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("Saved quality report.")
    return 0


def run_azure(provider: AzureDocumentIntelligenceProvider, sample_path: Path):
    start = time.perf_counter()
    ocr_result = provider.extract(sample_path)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return build_standard_ocr_from_safe_azure_ocr_result(
        ocr_result,
        source_file_name=sample_path.name,
    ), elapsed_ms


def run_paddle(provider: PaddleOCRProvider, sample_path: Path):
    start = time.perf_counter()
    result = provider.extract(sample_path, source_file_name=sample_path.name)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return result, elapsed_ms


def print_summary(item: dict[str, Any]) -> None:
    summary_by_provider = {
        row["provider"]: row
        for row in item["summary_rows"]
    }
    azure_status = summary_by_provider.get("azure", {}).get("provider_status")
    paddle_status = summary_by_provider.get("paddleocr", {}).get("provider_status")
    match_summary = item["match_summary"]
    print(
        "  status azure/paddle="
        f"{azure_status}/{paddle_status}, "
        f"matched={match_summary['matched_field_count']}, "
        f"azure_only={match_summary['azure_only_field_count']}, "
        f"paddle_only={match_summary['paddle_only_field_count']}, "
        f"mismatched={match_summary['mismatched_field_count']}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a safe Azure/PaddleOCR quality anchor batch.")
    parser.add_argument("--sample-dir", type=Path, default=Path("samples/receipts"))
    parser.add_argument("--output-dir", type=Path, default=Path("output/quality_runs"))
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=1)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
