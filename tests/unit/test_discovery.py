"""Tests for disambiguate.discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from disambiguate.discovery import (
    GlossaryNotFoundError,
    RepoRootNotFoundError,
    RootFileMissingError,
    expand_root_specs,
    find_glossary,
    find_repo_root,
    resolve_default_root,
)


def test_find_glossary_at_docs_glossary(tmp_path: Path) -> None:
    glossary = tmp_path / "docs" / "glossary"
    glossary.mkdir(parents=True)
    sub = tmp_path / "src"
    sub.mkdir()
    found = find_glossary(start=sub)
    assert found == glossary


def test_find_glossary_at_glossary(tmp_path: Path) -> None:
    glossary = tmp_path / "glossary"
    glossary.mkdir()
    found = find_glossary(start=tmp_path)
    assert found == glossary


def test_find_glossary_walks_up(tmp_path: Path) -> None:
    glossary = tmp_path / "docs" / "glossary"
    glossary.mkdir(parents=True)
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    found = find_glossary(start=deep)
    assert found == glossary


def test_find_glossary_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(GlossaryNotFoundError):
        find_glossary(start=tmp_path)


def test_find_repo_root_with_git(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert find_repo_root(start=deep) == tmp_path


def test_find_repo_root_raises_without_git(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    with pytest.raises(RepoRootNotFoundError):
        find_repo_root(start=deep)


def test_resolve_default_root(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    readme = tmp_path / "README.md"
    readme.write_text("hi", encoding="utf-8")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert resolve_default_root(start=deep) == [readme]


def test_resolve_default_root_missing_readme(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    with pytest.raises(RootFileMissingError):
        resolve_default_root(start=tmp_path)


def test_expand_root_specs_passes_through_existing_files(tmp_path: Path) -> None:
    a = tmp_path / "a.md"
    a.write_text("a", encoding="utf-8")
    b = tmp_path / "b.md"
    b.write_text("b", encoding="utf-8")
    result = expand_root_specs([str(a), str(b)])
    assert sorted(result) == sorted([a, b])


def test_expand_root_specs_expands_globs(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "b.md").write_text("b", encoding="utf-8")
    result = expand_root_specs([str(tmp_path / "*.md")])
    assert {p.name for p in result} == {"a.md", "b.md"}


def test_expand_root_specs_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(RootFileMissingError):
        expand_root_specs([str(tmp_path / "missing.md")])


def test_expand_root_specs_empty_glob_raises(tmp_path: Path) -> None:
    with pytest.raises(RootFileMissingError):
        expand_root_specs([str(tmp_path / "no-such-*.md")])
