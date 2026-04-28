"""Tests for `python -m disambiguate`."""

from __future__ import annotations

import subprocess
import sys


def test_python_module_requires_generated_terms() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "disambiguate", "--help"],
        capture_output=True,
    )
    assert result.returncode == 1
    assert b"disambiguate._terms" in result.stderr


def test_dunder_main_explain_requires_generated_terms() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "disambiguate", "--explain", "term"],
        capture_output=True,
    )
    assert result.returncode == 1
    assert b"disambiguate._terms" in result.stderr
