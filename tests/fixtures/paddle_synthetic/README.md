# Synthetic PaddleOCR Quality Fixtures

This directory contains sanitized synthetic OCR line fixtures for PaddleOCR parser
quality tests.

These files are not provider raw output and are not customer receipts. Each case
uses a small `paddle_lines` list shaped like safe OCR text blocks, then the test
helper converts those lines into `StandardOCRResult`.

Fixture rules:

- Use only synthetic `sample_id` and `source_file_name` values.
- Keep `source_file_name` prefixed with `synthetic_`.
- Do not store provider raw output, full OCR text, raw JSON, local absolute paths,
  endpoints, tokens, secrets, or API keys.
- Do not include full card numbers, full phone numbers, resident registration
  numbers, passwords, or WiFi passwords.
- For sensitive scenarios, use `[REDACTED]` plus `sensitive_category` only.
- Expected values are comparison baselines for key `ReceiptRecord` fields, not
  tax/accounting conclusions.
