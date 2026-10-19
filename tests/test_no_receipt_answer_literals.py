from pathlib import Path
import re


def test_real_recognition_code_contains_no_fixed_business_numbers_or_sample_file_names():
    root = Path(__file__).resolve().parents[1] / "app"
    for path in root.rglob("*.py"):
        if path.name == "mock_provider.py":
            continue  # Explicit demo provider; never an actual recognition path.
        source = path.read_text(encoding="utf-8")
        assert not re.search(r"(?<!\d)\d{3}-\d{2}-\d{5}(?!\d)", source), path.name
        assert "KakaoTalk_2026" not in source, path.name
