from __future__ import annotations

import pytest

from doc_tools.check import utils


def test_find_section_header_case_insensitive() -> None:
    lines = ["Intro", "## Document Controls", "Body"]
    assert utils.find_section_header(lines, "## document controls") == 1


def test_find_section_header_missing_raises() -> None:
    with pytest.raises(ValueError):
        utils.find_section_header(["## Intro"], "## Missing")


def test_extract_table_rows_captures_until_blank() -> None:
    lines = [
        "## Document Controls",
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Authors | Example |",
        "",
        "Next section",
    ]
    rows = utils.extract_table_rows(lines, 0)
    assert rows == ["| Field | Value |", "| --- | --- |", "| Authors | Example |"]


def test_parse_table_returns_data_rows() -> None:
    header, _, rows = utils.parse_table(
        ["| Field | Value |", "| --- | --- |", "| Authors | Example |", "| Version | 1.0 |"]
    )
    assert header == "| Field | Value |"
    assert rows == [("Authors", "Example"), ("Version", "1.0")]


def test_parse_table_requires_minimum_rows() -> None:
    with pytest.raises(ValueError):
        utils.parse_table(["| Field | Value |"])
