"""
Filesystem discovery: locate the glossary, the repo root, and lint roots.

These are the only modules that touch the filesystem outside of reading
specific files; centralizing them here keeps the rest of the code
deterministic and testable with synthetic data.
"""

from __future__ import annotations

import glob as _glob
import logging
import tomllib
from pathlib import Path

logger = logging.getLogger(__name__)


class GlossaryNotFoundError(Exception):
    """No `docs/glossary/` or `glossary/` directory found by walking up cwd."""


class RepoRootNotFoundError(Exception):
    """No `.git/` ancestor found — the working tree is not inside a git repo."""


class RootFileMissingError(Exception):
    """A root path or glob did not resolve to any existing file."""


_GLOSSARY_CANDIDATES = ("docs/glossary", "glossary")


def find_glossary(start: Path) -> Path:
    """
    Walk up from `start` looking for `docs/glossary/` or `glossary/`.

    start: directory to begin the search.

    Returns
    -------
    Path to the first matching glossary directory found.

    Raises
    ------
    GlossaryNotFoundError: no candidate exists between `start` and the
        filesystem root.

    """
    current = start.resolve()
    while True:
        for candidate in _GLOSSARY_CANDIDATES:
            path = current / candidate
            if path.is_dir():
                logger.info("found glossary at %s", path)
                return path
        if current.parent == current:
            raise GlossaryNotFoundError(
                f"No `docs/glossary/` or `glossary/` found walking up from {start}"
            )
        current = current.parent


def find_repo_root(start: Path) -> Path:
    """
    Walk up from `start` looking for a directory containing `.git/`.

    start: directory to begin the search.

    Returns
    -------
    Path to the first directory whose `.git` child exists.

    Raises
    ------
    RepoRootNotFoundError: walked all the way to the filesystem root without
        finding `.git/`.

    """
    current = start.resolve()
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            raise RepoRootNotFoundError(
                f"No `.git/` directory found walking up from {start}"
            )
        current = current.parent


def resolve_default_root(start: Path) -> list[Path]:
    """
    Return `[<repo-root>/README.md]`.

    start: directory to begin the repo-root search.

    Returns
    -------
    A single-element list containing the repository's top-level README.md.

    Raises
    ------
    RepoRootNotFoundError: no `.git/` ancestor exists.
    RootFileMissingError: the repo root has no README.md.

    """
    repo_root = find_repo_root(start=start)
    readme = repo_root / "README.md"
    if not readme.is_file():
        raise RootFileMissingError(f"Default root README.md not found at {readme}")
    return [readme]


def find_repo_url(repo_root: Path) -> str | None:
    """
    Return the canonical repository URL declared in `pyproject.toml`, or None.

    repo_root: directory containing `pyproject.toml`.

    Returns
    -------
    The string at `project.urls.repository` if present and a parseable URL,
    else None. Used by the orphan walker to recognize absolute links into
    this repo's own GitHub blob/tree URLs as internal cross-references.

    """
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.is_file():
        return None
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    urls = data.get("project", {}).get("urls", {})
    repo_url = urls.get("repository")
    if isinstance(repo_url, str) and repo_url:
        return repo_url
    return None


def expand_root_specs(specs: list[str]) -> list[Path]:
    """
    Expand a list of root-file specs (paths and/or globs) into existing files.

    specs: each entry is either a literal path or a glob pattern. Globs are
        expanded with `glob.glob`; literal paths are passed through. A spec
        that resolves to no existing files is an error.

    Returns
    -------
    Sorted list of unique resolved Path objects.

    Raises
    ------
    RootFileMissingError: any spec resolves to no files.

    """
    resolved: set[Path] = set()
    for spec in specs:
        # If it looks like a glob, expand it. Otherwise treat as a literal
        # path. `glob.glob` returns [] for both "no match" and "literal path
        # that does not exist", so we differentiate up front.
        is_glob_pattern = any(ch in spec for ch in "*?[")
        if is_glob_pattern:
            matches = _glob.glob(spec, recursive=True)
            if not matches:
                raise RootFileMissingError(f"Root glob matched no files: {spec!r}")
            for match in matches:
                path = Path(match).resolve()
                if not path.is_file():
                    continue
                resolved.add(path)
        else:
            path = Path(spec).resolve()
            if not path.is_file():
                raise RootFileMissingError(f"Root file not found: {spec!r}")
            resolved.add(path)
    return sorted(resolved)
