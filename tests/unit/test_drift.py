"""Tests for disambiguate.drift — the drift-check engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from disambiguate.drift import run_drift_checks
from disambiguate.glossary import load_glossary


def _write(directory: Path, name: str, body: str) -> Path:
    path = directory / f"{name}.md"
    path.write_text(body, encoding="utf-8")
    return path


def _setup_glossary(tmp_path: Path) -> Path:
    glossary_dir = tmp_path / "glossary"
    glossary_dir.mkdir()
    return glossary_dir


@pytest.mark.xfail(strict=True)
def test_unlinked_mention_produces_one_finding(tmp_path: Path) -> None:
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    root = _write(
        tmp_path,
        "README",
        "[w](glossary/widget.md)\n",
    )
    doc = _write(
        tmp_path,
        "guide",
        "The widget spins. Later the widget stops.\n",
    )
    root.write_text(
        "[w](glossary/widget.md) [guide](guide.md)\n",
        encoding="utf-8",
    )
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    unlinked = [f for f in findings if f.rule_code == "unlinked-term"]
    assert len(unlinked) == 1
    assert unlinked[0].term == "widget"
    assert unlinked[0].path == doc
    assert unlinked[0].line == 1


@pytest.mark.xfail(strict=True)
def test_linked_once_silences_later_plain_mentions(tmp_path: Path) -> None:
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    root = _write(
        tmp_path,
        "README",
        "A [widget](glossary/widget.md) spins. Later the widget stops.\n",
    )
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []
