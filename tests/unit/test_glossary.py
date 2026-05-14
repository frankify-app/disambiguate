"""Tests for disambiguate.glossary."""

from __future__ import annotations

from pathlib import Path

import pytest

from disambiguate.glossary import (
    DuplicateSlugError,
    Term,
    load_glossary,
)


def _write_term(directory: Path, slug: str, body: str) -> None:
    (directory / f"{slug}.md").write_text(body, encoding="utf-8")


def test_loads_terms_from_directory(tmp_path: Path) -> None:
    _write_term(tmp_path, "term", "## Term\n\nbody\n")
    _write_term(tmp_path, "slug", "## Slug\n\nrefs [term](term.md)\n")
    glossary = load_glossary(tmp_path)
    assert set(glossary.terms) == {"term", "slug"}
    assert glossary.terms["slug"].canonical_name == "Slug"
    assert glossary.terms["slug"].link_slugs == ["term"]


def test_dependency_graph_only_keeps_known_slugs(tmp_path: Path) -> None:
    _write_term(tmp_path, "a", "## A\n\nrefs [b](b.md), [unknown](unknown.md)\n")
    _write_term(tmp_path, "b", "## B\n\nbody\n")
    glossary = load_glossary(tmp_path)
    assert glossary.dependencies["a"] == {"b"}


def test_dependency_graph_includes_all_known() -> None:
    pass


def test_unknown_slugs_recorded_separately(tmp_path: Path) -> None:
    _write_term(tmp_path, "a", "## A\n\nrefs [foo](foo.md), [bar](bar.md)\n")
    glossary = load_glossary(tmp_path)
    assert glossary.broken_links["a"] == ["foo", "bar"]


def test_duplicate_slugs_raise(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    _write_term(tmp_path, "foo", "## Foo\n\n")
    _write_term(sub, "foo", "## Foo dup\n\n")
    with pytest.raises(DuplicateSlugError):
        load_glossary(tmp_path)


def test_term_has_path(tmp_path: Path) -> None:
    _write_term(tmp_path, "term", "## Term\n\n")
    glossary = load_glossary(tmp_path)
    term = glossary.terms["term"]
    assert isinstance(term, Term)
    assert term.path == tmp_path / "term.md"


def test_glossary_has_root(tmp_path: Path) -> None:
    glossary = load_glossary(tmp_path)
    assert glossary.root == tmp_path
