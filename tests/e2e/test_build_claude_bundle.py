"""End-to-end tests for the Claude release bundle."""

from __future__ import annotations

import subprocess
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _project_version() -> str:
    """Return the version from pyproject.toml."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version: str = pyproject["project"]["version"]
    return version


def _run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    """Run a command from the repo root and return its completed process."""
    return subprocess.run(  # noqa: S603 - commands are controlled test data.
        command,
        check=True,
        capture_output=True,
        cwd=cwd,
        text=True,
    )


def test_claude_bundle_installs_offline_and_reports_version(tmp_path: Path) -> None:
    """Build the bundle, install from it offline, and execute --version."""
    version = _project_version()
    _run(["make", f"dist/disambiguate-v{version}-claude-bundle.zip"])

    bundle = ROOT / "dist" / f"disambiguate-v{version}-claude-bundle.zip"
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    with zipfile.ZipFile(bundle) as archive:
        archive.extractall(bundle_dir)

    venv = tmp_path / "venv"
    _run(["python", "-m", "venv", str(venv)])
    pip = venv / "bin" / "pip"
    disambiguate = venv / "bin" / "disambiguate"
    _run(
        [
            str(pip),
            "install",
            "--no-index",
            "--find-links",
            str(bundle_dir),
            f"disambiguate=={version}",
        ]
    )

    result = _run([str(disambiguate), "--version"])
    assert result.stdout.strip() == f"disambiguate {version}"
