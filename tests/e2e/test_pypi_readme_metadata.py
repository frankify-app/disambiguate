"""End-to-end test: built package metadata carries absolute README links."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

GITHUB_BLOB_PREFIX = "https://github.com/frankify-app/disambiguate/blob/main/"


def _run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    """Run a command from the repo root and return its completed process."""
    return subprocess.run(  # noqa: S603 - commands are controlled test data.
        command,
        check=True,
        capture_output=True,
        cwd=cwd,
        text=True,
    )


def test_wheel_long_description_uses_absolute_github_links(tmp_path: Path) -> None:
    """`uv build` produces METADATA whose long description links are absolute."""
    _run(["uv", "build", "--wheel", "--out-dir", str(tmp_path)])

    [wheel] = tmp_path.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        [metadata_name] = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        metadata = archive.read(metadata_name).decode("utf-8")

    assert f"({GITHUB_BLOB_PREFIX}docs/glossary/term.md)" in metadata
    assert f"({GITHUB_BLOB_PREFIX}CONTRIBUTING.md)" in metadata
    assert "](docs/" not in metadata
    assert "](CONTRIBUTING.md)" not in metadata
    assert "img.shields.io" in metadata, "badge images should survive rewriting"
