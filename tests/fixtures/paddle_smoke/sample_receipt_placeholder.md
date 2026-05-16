# Placeholder Only

This is not an OCR input file.

For the opt-in smoke test, provide a local non-sensitive image with:

```powershell
$env:RUN_PADDLEOCR_TESTS = "1"
$env:PADDLEOCR_TEST_IMAGE_PATH = "<local-safe-sample-image>"
python -m pytest tests/integration/test_paddle_ocr_provider_smoke.py
```

Keep real customer images and full local paths out of the repository and reports.
