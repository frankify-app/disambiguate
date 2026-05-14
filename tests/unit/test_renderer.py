"""Tests for disambiguate.renderer."""

from __future__ import annotations

from pathlib import Path

from disambiguate.glossary import Term
from disambiguate.renderer import build_explain_preamble, render_terms


def _term(slug: str, body: str) -> Term:
    return Term(
        slug=slug,
        canonical_name=slug.title(),
        body=body,
        link_slugs=[],
        path=Path(f"/tmp/{slug}.md"),
    )


def test_renders_terms_concatenated_with_separator() -> None:
    terms = [
        _term("a", "## A\n\nfoo\n"),
        _term("b", "## B\n\nbar\n"),
    ]
    out = render_terms(terms)
    assert "## A" in out
    assert "## B" in out
    assert "foo" in out
    assert "bar" in out
    assert out.index("## A") < out.index("## B")


def test_render_with_preamble() -> None:
    terms = [_term("a", "## A\n\nfoo\n")]
    preamble = "PREAMBLE\n\n---\n\n"
    out = render_terms(terms, preamble=preamble)
    assert out.startswith("PREAMBLE")
    assert "## A" in out


def test_explain_preamble_no_args() -> None:
    preamble = build_explain_preamble([])
    assert "disambiguate\n" in preamble or "disambiguate`" in preamble
    assert "topological" in preamble.lower()
    assert preamble.endswith("\n\n---\n\n")


def test_explain_preamble_with_terms() -> None:
    preamble = build_explain_preamble(["topological-order", "lint"])
    assert "disambiguate topological-order lint" in preamble


def test_explain_preamble_quotes_special_terms() -> None:
    preamble = build_explain_preamble(["a b"])
    assert "'a b'" in preamble


def test_renders_body_verbatim() -> None:
    body = "## Term\n\nFoo [bar](bar.md) baz.\n"
    out = render_terms([_term("term", body)])
    assert body in out
