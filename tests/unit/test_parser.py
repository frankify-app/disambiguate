"""Tests for disambiguate.parser."""

from __future__ import annotations

from disambiguate.parser import ParsedTerm, parse_term_text


def test_parses_h2_heading() -> None:
    text = "## Term\n\nA unit of vocabulary.\n"
    parsed = parse_term_text("term", text)
    assert parsed == ParsedTerm(
        slug="term",
        canonical_name="Term",
        body=text,
        link_slugs=[],
    )


def test_first_h2_is_canonical_name() -> None:
    text = "# Title\n\n## First\n\nbody\n\n## Second\n"
    parsed = parse_term_text("foo", text)
    assert parsed.canonical_name == "First"


def test_missing_h2_returns_none_canonical() -> None:
    text = "# Only an H1\n\nbody\n"
    parsed = parse_term_text("foo", text)
    assert parsed.canonical_name is None


def test_extracts_markdown_link_basenames() -> None:
    text = "## Foo\n\nSee [bar](bar.md) and [baz](path/to/baz.md).\n"
    parsed = parse_term_text("foo", text)
    assert parsed.link_slugs == ["bar", "baz"]


def test_extracts_wikilink_basenames() -> None:
    text = "## Foo\n\nSee [[bar]] and [[baz]].\n"
    parsed = parse_term_text("foo", text)
    assert parsed.link_slugs == ["bar", "baz"]


def test_mixed_link_syntaxes() -> None:
    text = "## Foo\n\nSee [bar](bar.md) and [[baz]].\n"
    parsed = parse_term_text("foo", text)
    assert parsed.link_slugs == ["bar", "baz"]


def test_ignores_links_inside_fenced_code_block() -> None:
    text = "## Foo\n\n```\n[bar](bar.md)\n[[baz]]\n```\nReal link: [qux](qux.md).\n"
    parsed = parse_term_text("foo", text)
    assert parsed.link_slugs == ["qux"]


def test_ignores_links_inside_tilde_fenced_code_block() -> None:
    text = "## Foo\n\n~~~\n[[bar]]\n~~~\n[real](real.md)\n"
    parsed = parse_term_text("foo", text)
    assert parsed.link_slugs == ["real"]


def test_ignores_links_inside_inline_code() -> None:
    text = (
        "## Foo\n\nUse `[[foo]]` syntax. Also `[label](foo.md)`. Real: [bar](bar.md).\n"
    )
    parsed = parse_term_text("foo", text)
    assert parsed.link_slugs == ["bar"]


def test_ignores_external_urls_and_non_md_links() -> None:
    text = (
        "## Foo\n\n"
        "External: [link](https://example.com).\n"
        "Image: [pic](pic.png).\n"
        "Md link: [bar](bar.md).\n"
    )
    parsed = parse_term_text("foo", text)
    assert parsed.link_slugs == ["bar"]


def test_link_basename_strips_path_components() -> None:
    text = "## Foo\n\n[a](a.md) [b](sub/b.md) [c](deep/sub/c.md)\n"
    parsed = parse_term_text("foo", text)
    assert parsed.link_slugs == ["a", "b", "c"]


def test_duplicate_links_preserved() -> None:
    text = "## Foo\n\n[a](a.md) [a](a.md) [a-other-text](a.md)\n"
    parsed = parse_term_text("foo", text)
    assert parsed.link_slugs == ["a", "a", "a"]


def test_body_includes_full_text() -> None:
    text = "## Foo\n\nFirst para.\n\nSecond para.\n"
    parsed = parse_term_text("foo", text)
    assert parsed.body == text


def test_wikilink_with_display_text_resolves_to_slug() -> None:
    text = "## Foo\n\nSee [[bar|the bar thing]].\n"
    parsed = parse_term_text("foo", text)
    assert parsed.link_slugs == ["bar"]


def test_malformed_pipe_wikilinks_resolve_on_first_segment() -> None:
    # Obsidian-lenient: everything after the first pipe is display text,
    # even when empty or containing further pipes. Empty target = no link.
    text = "## Foo\n\n[[bar|]] and [[baz|b|c]] and [[|only display]].\n"
    parsed = parse_term_text("foo", text)
    assert parsed.link_slugs == ["bar", "baz"]


def test_wikilink_fragment_targets_resolve_to_slug() -> None:
    text = "## Foo\n\n[[bar#My Heading]] and [[baz#^block-id|shown text]].\n"
    parsed = parse_term_text("foo", text)
    assert parsed.link_slugs == ["bar", "baz"]


def test_h2_with_extra_hashes_not_treated_as_h2() -> None:
    text = "### H3\n\nbody\n"
    parsed = parse_term_text("foo", text)
    assert parsed.canonical_name is None
