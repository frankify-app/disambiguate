"""Tests for release-oriented Make targets."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[2]


def _make_executable() -> str:
    """Return the absolute make executable path for subprocess tests."""
    make = which("make")
    assert make is not None
    return make


def _make_dry_run(target: str) -> str:
    """Return the commands make would run for target without executing them."""
    result = subprocess.run(  # noqa: S603 - target is controlled test data.
        [_make_executable(), "--no-print-directory", "-n", target],
        check=True,
        capture_output=True,
        cwd=ROOT,
        text=True,
    )
    stdout: str = result.stdout
    return stdout


def _project_version() -> str:
    """Return the version from pyproject.toml."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version: str = pyproject["project"]["version"]
    return version


def test_claude_bundle_artifact_target_passes_version_from_filename() -> None:
    output = _make_dry_run("dist/disambiguate-v1.2.3-claude-bundle.zip")

    assert 'bash scripts/build_claude_bundle.sh "1.2.3"' in output


def test_build_claude_bundle_uses_project_version_artifact() -> None:
    version = _project_version()
    output = _make_dry_run("build-claude-bundle")

    assert f"make dist/disambiguate-v{version}-claude-bundle.zip" in output
    assert f'bash scripts/build_claude_bundle.sh "{version}"' in output


def test_developer_targets_run_dev_cli() -> None:
    main_output = _make_dry_run("main")
    explain_output = _make_dry_run("explain")
    dogfood_output = _make_dry_run("dogfood")

    assert "uv run python dev_cli.py\n" in main_output
    assert "uv run python dev_cli.py --explain\n" in explain_output
    assert "uv run python dev_cli.py --lint\n" in dogfood_output


def test_explain_does_not_build_package() -> None:
    output = _make_dry_run("explain")

    assert "uv build" not in output
