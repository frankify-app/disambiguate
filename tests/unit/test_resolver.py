"""Tests for disambiguate.resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from disambiguate.glossary import Glossary, Term
from disambiguate.resolver import (
    CycleError,
    UnknownSlugError,
    resolve,
)


def _term(slug: str, deps: list[str]) -> Term:
    body = "## " + slug.title() + "\n\n"
    body += "".join(f"[{d}]({d}.md)\n" for d in deps)
    return Term(
        slug=slug,
        canonical_name=slug.title(),
        body=body,
        link_slugs=deps,
        path=Path(f"/tmp/{slug}.md"),
    )


def _glossary(*terms: Term) -> Glossary:
    by_slug = {t.slug: t for t in terms}
    deps = {t.slug: {d for d in t.link_slugs if d in by_slug} for t in terms}
    return Glossary(
        root=Path("/tmp"),
        terms=by_slug,
        dependencies=deps,
        broken_links={},
    )


def test_resolves_single_term_with_no_deps() -> None:
    glossary = _glossary(_term("a", []))
    result = resolve(glossary, ["a"])
    assert [t.slug for t in result] == ["a"]


def test_resolves_chain_in_topo_order() -> None:
    glossary = _glossary(
        _term("a", ["b"]),
        _term("b", ["c"]),
        _term("c", []),
    )
    result = resolve(glossary, ["a"])
    assert [t.slug for t in result] == ["c", "b", "a"]


def test_resolves_diamond() -> None:
    glossary = _glossary(
        _term("top", ["left", "right"]),
        _term("left", ["bottom"]),
        _term("right", ["bottom"]),
        _term("bottom", []),
    )
    result = resolve(glossary, ["top"])
    slugs = [t.slug for t in result]
    assert slugs[0] == "bottom"
    assert slugs[-1] == "top"
    assert set(slugs) == {"top", "left", "right", "bottom"}
    assert slugs.index("left") < slugs.index("top")
    assert slugs.index("right") < slugs.index("top")


def test_resolves_multiple_requested_slugs() -> None:
    glossary = _glossary(
        _term("a", ["b"]),
        _term("b", []),
        _term("c", []),
    )
    result = resolve(glossary, ["a", "c"])
    slugs = [t.slug for t in result]
    assert set(slugs) == {"a", "b", "c"}
    assert slugs.index("b") < slugs.index("a")


def test_unknown_slug_raises() -> None:
    glossary = _glossary(_term("a", []))
    with pytest.raises(UnknownSlugError) as info:
        resolve(glossary, ["b"])
    assert "b" in str(info.value)


def test_cycle_raises() -> None:
    glossary = _glossary(
        _term("a", ["b"]),
        _term("b", ["a"]),
    )
    with pytest.raises(CycleError):
        resolve(glossary, ["a"])


def test_no_slugs_resolves_entire_glossary() -> None:
    glossary = _glossary(
        _term("a", ["b"]),
        _term("b", []),
        _term("c", []),
    )
    result = resolve(glossary, [])
    slugs = [t.slug for t in result]
    assert set(slugs) == {"a", "b", "c"}
    assert slugs.index("b") < slugs.index("a")


def test_each_term_appears_once() -> None:
    glossary = _glossary(
        _term("top", ["a", "b"]),
        _term("a", ["shared"]),
        _term("b", ["shared"]),
        _term("shared", []),
    )
    result = resolve(glossary, ["top"])
    slugs = [t.slug for t in result]
    assert len(slugs) == len(set(slugs))


def test_stable_ordering() -> None:
    glossary = _glossary(
        _term("a", []),
        _term("b", []),
        _term("c", []),
    )
    first = [t.slug for t in resolve(glossary, [])]
    second = [t.slug for t in resolve(glossary, [])]
    assert first == second
