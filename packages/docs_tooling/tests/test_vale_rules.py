from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALE_CONFIG = ROOT / "config" / "vale-ci.ini"
FIXTURES = ROOT / "tests" / "vale_fixtures"


pytestmark = pytest.mark.skipif(
    shutil.which("vale") is None,
    reason="Vale CLI is not available in the current environment.",
)


def ensure_vale_packages() -> None:
    subprocess.run(
        [
            "vale",
            "sync",
            "--config",
            str(VALE_CONFIG),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def run_vale(target: Path) -> subprocess.CompletedProcess[str]:
    ensure_vale_packages()
    return subprocess.run(
        [
            "vale",
            "--config",
            str(VALE_CONFIG),
            str(target),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_vale_passes_on_valid_fixture() -> None:
    result = run_vale(FIXTURES / "service_valid.md")

    assert result.returncode == 0, result.stderr


def test_vale_flags_missing_preamble_divider() -> None:
    result = run_vale(FIXTURES / "service_missing_divider.md")

    assert result.returncode != 0
    assert "uDocket-Core.PreambleDivider" in result.stdout + result.stderr


def test_vale_flags_appendix_reference_format() -> None:
    result = run_vale(FIXTURES / "service_bad_appendix.md")

    assert result.returncode != 0
    assert "uDocket-Policy.Citations" in result.stdout + result.stderr
