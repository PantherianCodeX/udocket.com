from __future__ import annotations
import json
from pathlib import Path
import pytest

from packages.udocket_core.models.identifiers.engine import validate_case_number

SCHEMES = Path("packages/udocket_core/data/courts/ca/ab/case_number_schemes.json")

@pytest.mark.parametrize("court_key", ["CA-AB-KB", "CA-AB-ACJ", "CA-AB-ABCA"])
def test_examples_valid_and_invalid(court_key: str):
    raw = json.loads(SCHEMES.read_text(encoding="utf-8"))
    block = [d for d in raw["data"] if d["court_key"] == court_key][0]
    for v in block.get("examples_valid", []):
        cn = validate_case_number(v, court_key_hint=court_key)
        assert cn.court_key == court_key
        assert cn.parts.get("year")
        assert cn.parts.get("loc")
        assert cn.parts.get("seq")

    for inv in block.get("examples_invalid", []):
        with pytest.raises(Exception):
            validate_case_number(inv, court_key_hint=court_key)

def test_autodetect_across_all_schemes():
    # should match KB
    cn = validate_case_number("2301-123456")
    assert cn.court_key == "CA-AB-KB"
