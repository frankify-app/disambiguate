"""Tests for the source-checkout development CLI."""

from __future__ import annotations

import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[2]


def _uv_executable() -> str:
    """Return the absolute uv executable path for subprocess tests."""
    uv = which("uv")
    assert uv is not None
    return uv


def _run_dev_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run dev_cli.py from the repository root."""
    return subprocess.run(  # noqa: S603 - args are controlled test data.
        [sys.executable, "dev_cli.py", *args],
        check=True,
        capture_output=True,
        cwd=ROOT,
        text=True,
    )


def test_dev_cli_explain_reads_source_glossary() -> None:
    result = _run_dev_cli("--explain", "term")

    assert "## Term" in result.stdout


def test_dev_cli_explain_normalizes_phrase() -> None:
    result = _run_dev_cli("--explain", "topological order")

    assert "## Topological order" in result.stdout


def test_dev_cli_from_without_value_reads_stdin() -> None:
    result = subprocess.run(
        [sys.executable, "dev_cli.py", "--from"],
        check=True,
        capture_output=True,
        cwd=ROOT,
        input="see [[term]]\n",
        text=True,
    )

    assert "## Term" in result.stdout


def test_dev_cli_is_not_in_built_distributions() -> None:
    subprocess.run(  # noqa: S603 - command is controlled test data.
        [_uv_executable(), "build"],
        check=True,
        cwd=ROOT,
    )

    with zipfile.ZipFile(ROOT / "dist/disambiguate-0.0.0-py3-none-any.whl") as wheel:
        assert "dev_cli.py" not in wheel.namelist()

    with tarfile.open(ROOT / "dist/disambiguate-0.0.0.tar.gz") as sdist:
        assert "disambiguate-0.0.0/dev_cli.py" not in {
            member.name for member in sdist.getmembers()
        }
