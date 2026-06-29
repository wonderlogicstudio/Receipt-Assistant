from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.classifier.merchant_importer import MerchantImportResult, PublicMerchantCsvImporter
from app.db.merchant_repository import MerchantRepository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import public store CSV data as merchant review candidates.")
    parser.add_argument("csv_path", help="Local public store CSV path. The file itself is not copied into the repo.")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV encoding. Default: utf-8-sig")
    parser.add_argument("--batch-id", default=None, help="Optional import batch id.")
    args = parser.parse_args(argv)

    csv_path = Path(args.csv_path)
    repository = MerchantRepository()
    importer = PublicMerchantCsvImporter(repository)
    result = importer.import_csv(csv_path, encoding=args.encoding, source_batch_id=args.batch_id)

    print(format_import_summary(result))
    return 0


def format_import_summary(result: MerchantImportResult) -> str:
    return (
        "Imported merchant candidates "
        f"file={Path(str(result.source_file_name or 'merchant.csv')).name} "
        f"batch={result.source_batch_id} "
        f"scanned={result.scanned_row_count} "
        f"imported={result.imported_row_count} "
        f"skipped={result.skipped_row_count} "
        f"skipped_duplicate={result.skipped_duplicate_row_count} "
        f"skipped_invalid={result.skipped_invalid_row_count} "
        f"duplicate_file={result.duplicate_file} "
        f"elapsed_seconds={result.elapsed_seconds:.3f} "
        f"rows_per_second={result.rows_per_second:.2f}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
