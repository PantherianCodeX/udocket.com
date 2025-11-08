from __future__ import annotations

from typing import List

import pytest

import doc_tools.lint_docs as lint_docs


def test_lint_docs_forwards_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: List[List[str]] = []

    def fake_manage(args):  # type: ignore[no-untyped-def]
        captured.append(list(args))
        return 0

    monkeypatch.setattr(lint_docs, "manage_main", fake_manage)

    rc = lint_docs.main(["--target", "docs/overview"])

    assert rc == 0
    assert captured == [["--lint", "--target", "docs/overview"]]


def test_lint_docs_defaults_to_sys_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: List[List[str]] = []

    def fake_manage(args):  # type: ignore[no-untyped-def]
        captured.append(list(args))
        return 0

    monkeypatch.setattr(lint_docs, "manage_main", fake_manage)
    monkeypatch.setattr(lint_docs.sys, "argv", ["lint_docs.py", "--dry-run"])

    rc = lint_docs.main(None)

    assert rc == 0
    assert captured == [["--lint", "--dry-run"]]
