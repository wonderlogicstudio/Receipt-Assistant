# PaddleOCR Smoke Test Fixture Guidance

Do not commit real receipt images or customer files in this directory.

Use `PADDLEOCR_TEST_IMAGE_PATH` to point the opt-in smoke test at a local image
outside the repository. The image should be synthetic or a non-sensitive sample.

Rules:

- Do not use images containing card numbers, resident registration numbers,
  phone numbers, addresses, WiFi credentials, or other sensitive values.
- Do not share full local paths in reports; mention the file name only.
- Do not add PDF files for the Week 9-D smoke test. PDF handling is deferred.
- Do not commit generated model files, OCR raw output, or real customer files.
