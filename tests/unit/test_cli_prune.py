"""
End-to-end tests for the `prune` verb.

`prune` is the only command that deletes files, so these exercise it
through `main` against a real tree rather than at the planning layer.
"""

from __future__ import annotations

import io
import os
import sys
import types
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from disambiguate.cli import main

CONSENT = "<!-- d10e: auto-prune -->"


@pytest.fixture(autouse=True)
def _use_generated_terms_index(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide generated `_terms.py` data for source-tree CLI unit tests."""
    terms_module = types.ModuleType("disambiguate._terms")
    terms_module.__dict__["TERMS"] = ("basename-resolution", "term")
    monkeypatch.setitem(sys.modules, "disambiguate._terms", terms_module)


def run(argv: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run cli.main with cwd and return (exit_code, stdout, stderr)."""
    out = io.StringIO()
    err = io.StringIO()
    original_cwd = Path.cwd()
    try:
        os.chdir(cwd)
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
    finally:
        os.chdir(original_cwd)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A repo whose README links one of three terms."""
    (tmp_path / ".git").mkdir()
    glossary = tmp_path / "docs" / "glossary"
    glossary.mkdir(parents=True)
    (glossary / "kept.md").write_text(
        f"## Kept\n\n{CONSENT}\n\nLinked from the README.\n", encoding="utf-8"
    )
    (glossary / "vendored.md").write_text(
        f"## Vendored\n\n{CONSENT}\n\nArrived unlinked.\n", encoding="utf-8"
    )
    (glossary / "local.md").write_text(
        "## Local\n\nRepo-owned, never consented.\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text(
        "See [kept](docs/glossary/kept.md).\n", encoding="utf-8"
    )
    return tmp_path


def test_prune_deletes_consenting_orphans_only(project: Path) -> None:
    """The default run removes what consented and nothing else."""
    code, _, _ = run(["prune"], project)

    glossary = project / "docs" / "glossary"
    assert code == 0
    assert (glossary / "kept.md").exists()
    assert not (glossary / "vendored.md").exists()
    assert (glossary / "local.md").exists()


def test_prune_dry_run_deletes_nothing_and_names_the_widening_flag(
    project: Path,
) -> None:
    """--dry-run lists both sets and makes --all-orphans discoverable."""
    code, stdout, _ = run(["prune", "--dry-run"], project)

    glossary = project / "docs" / "glossary"
    assert code == 0
    assert (glossary / "vendored.md").exists(), "--dry-run must not delete"
    assert "vendored" in stdout
    assert "local" in stdout
    assert "--all-orphans" in stdout


def test_prune_all_orphans_also_removes_terms_that_never_consented(
    project: Path,
) -> None:
    code, _, _ = run(["prune", "--all-orphans"], project)

    glossary = project / "docs" / "glossary"
    assert code == 0
    assert (glossary / "kept.md").exists()
    assert not (glossary / "vendored.md").exists()
    assert not (glossary / "local.md").exists()


def test_prune_leaves_the_glossary_lint_clean(project: Path) -> None:
    """The point of the feature: --lint passes after pruning."""
    assert run(["--lint"], project)[0] == 1

    run(["prune", "--all-orphans"], project)

    assert run(["--lint"], project)[0] == 0
