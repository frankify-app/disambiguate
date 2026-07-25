"""Tests for disambiguate.from_mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from disambiguate.from_mode import BrokenFromLinkError, extract_slugs
from disambiguate.glossary import Glossary, Term


def _glossary(*slugs: str) -> Glossary:
    terms = {
        slug: Term(
            slug=slug,
            canonical_name=slug,
            body=f"## {slug}\n",
            link_slugs=[],
            path=Path(f"/tmp/{slug}.md"),
        )
        for slug in slugs
    }
    return Glossary(
        root=Path("/tmp"),
        terms=terms,
        dependencies={s: set() for s in slugs},
        broken_links={},
    )


def test_extracts_md_links() -> None:
    text = "see [a](a.md) and [b](path/to/b.md)"
    slugs = extract_slugs(text, _glossary("a", "b"))
    assert slugs == ["a", "b"]


def test_extracts_wikilinks() -> None:
    text = "[[a]] and [[b]]"
    slugs = extract_slugs(text, _glossary("a", "b"))
    assert slugs == ["a", "b"]


def test_dedupes_preserving_first_occurrence() -> None:
    text = "[[b]] and [a](a.md) and [b again](b.md) and [[a]]"
    slugs = extract_slugs(text, _glossary("a", "b"))
    assert slugs == ["b", "a"]


def test_ignores_external_urls() -> None:
    text = "see [home](https://example.com) and [a](a.md)"
    slugs = extract_slugs(text, _glossary("a"))
    assert slugs == ["a"]


def test_ignores_url_to_md_file() -> None:
    text = "see [up](https://example.com/foo.md)"
    slugs = extract_slugs(text, _glossary("a"))
    assert slugs == []


def test_ignores_non_md_links() -> None:
    text = "[pic](pic.png) and [a](a.md)"
    slugs = extract_slugs(text, _glossary("a"))
    assert slugs == ["a"]


def test_broken_md_link_raises() -> None:
    text = "[ghost](ghost.md)"
    with pytest.raises(BrokenFromLinkError):
        extract_slugs(text, _glossary("a"))


def test_broken_wikilink_raises() -> None:
    text = "[[ghost]]"
    with pytest.raises(BrokenFromLinkError):
        extract_slugs(text, _glossary("a"))


def test_ignores_links_in_code_blocks() -> None:
    text = "```\n[ghost](ghost.md)\n[[ghost]]\n```\n[a](a.md)\n"
    slugs = extract_slugs(text, _glossary("a"))
    assert slugs == ["a"]


def test_extracts_display_text_and_fragment_links() -> None:
    text = "[[a|shown text]] then [detail](b.md#section) then [[c#Heading|x]]"
    slugs = extract_slugs(text, _glossary("a", "b", "c"))
    assert slugs == ["a", "b", "c"]


def test_broken_slug_behind_display_text_fails() -> None:
    text = "[[ghost|friendly name]]"
    with pytest.raises(BrokenFromLinkError, match="ghost"):
        extract_slugs(text, _glossary("a"))


def test_link_to_existing_non_glossary_doc_is_ignored(tmp_path: Path) -> None:
    """
    Kata for #45: existing non-glossary link targets are document links.

    A `.md` link that resolves to a real file outside the glossary must not
    be classified as a broken glossary reference.
    """
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    source = tmp_path / "README.md"
    text = "See [a](a.md) and [the changelog](CHANGELOG.md).\n"
    source.write_text(text, encoding="utf-8")
    slugs = extract_slugs(text, _glossary("a"), source_path=source)
    assert slugs == ["a"]
