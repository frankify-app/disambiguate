"""Tests for disambiguate.parser."""

from __future__ import annotations

from disambiguate.parser import (
    ParsedTerm,
    extract_md_link_paths_with_urls,
    github_url_to_repo_path,
    parse_term_text,
)


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


def test_h2_with_extra_hashes_not_treated_as_h2() -> None:
    text = "### H3\n\nbody\n"
    parsed = parse_term_text("foo", text)
    assert parsed.canonical_name is None


_REPO = "https://github.com/frankify-app/disambiguate"


def test_extract_md_link_paths_with_urls_keeps_urls() -> None:
    text = (
        f"[a](a.md) [b]({_REPO}/blob/main/docs/glossary/b.md) "
        "[c](https://example.com/c.md)\n"
    )
    assert extract_md_link_paths_with_urls(text) == [
        "a.md",
        f"{_REPO}/blob/main/docs/glossary/b.md",
        "https://example.com/c.md",
    ]


def test_github_url_to_repo_path_blob() -> None:
    url = f"{_REPO}/blob/main/docs/glossary/term.md"
    assert github_url_to_repo_path(url, _REPO) == "docs/glossary/term.md"


def test_github_url_to_repo_path_raw() -> None:
    url = (
        "https://raw.githubusercontent.com/frankify-app/disambiguate/"
        "main/docs/glossary/term.md"
    )
    assert github_url_to_repo_path(url, _REPO) == "docs/glossary/term.md"


def test_github_url_to_repo_path_strips_fragment() -> None:
    url = f"{_REPO}/blob/main/docs/glossary/term.md#anchor"
    assert github_url_to_repo_path(url, _REPO) == "docs/glossary/term.md"


def test_github_url_to_repo_path_rejects_other_repo() -> None:
    url = "https://github.com/other/proj/blob/main/x.md"
    assert github_url_to_repo_path(url, _REPO) is None


def test_github_url_to_repo_path_rejects_non_github_url() -> None:
    assert github_url_to_repo_path("https://example.com/x.md", _REPO) is None


def test_github_url_to_repo_path_accepts_repo_url_with_dot_git() -> None:
    url = f"{_REPO}/blob/main/docs/x.md"
    assert github_url_to_repo_path(url, _REPO + ".git") == "docs/x.md"
