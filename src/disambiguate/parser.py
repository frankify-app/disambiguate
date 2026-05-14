"""
Parse a single glossary term file.

A term is a markdown file. The first H2 heading is the canonical name; the
file basename (with `.md` stripped) is the slug; the full text is the body;
markdown and wikilink cross-references resolve to slugs by basename.

Code blocks (fenced ``` or ~~~) and inline code spans (single backticks) are
stripped before link extraction so that example link syntax in code never
counts as a real cross-reference.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedTerm:
    """
    The result of parsing a single term file.

    slug: stable identifier (file basename without `.md`).
    canonical_name: text of the first H2 heading, or None if no H2 found.
    body: the full original markdown text, returned verbatim for rendering.
    link_slugs: cross-reference targets, in document order, duplicates preserved.
        External URLs, non-`.md` links, and links inside any kind of code are
        excluded.
    """

    slug: str
    canonical_name: str | None
    body: str
    link_slugs: list[str]


_FENCED_CODE_RE = re.compile(
    r"^(?P<fence>```+|~~~+)[^\n]*\n.*?^(?P=fence)\s*$",
    re.MULTILINE | re.DOTALL,
)

# Inline code: a run of one-or-more backticks, then content, then the same
# count of backticks. Match shortest content. Does not span multiple lines —
# fenced blocks handle that.
_INLINE_CODE_RE = re.compile(r"(?P<ticks>`+)(?!`).*?(?P=ticks)")

_H2_RE = re.compile(r"^##\s+(?P<name>.+?)\s*$", re.MULTILINE)

# Standard markdown link to an .md file: [text](path/to/foo.md)
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+\.md)(?:\s+\"[^\"]*\")?\)")

# Wikilink: [[slug]] (no spaces inside the slug, conservative)
_WIKILINK_RE = re.compile(r"\[\[([^\[\]|\s]+)\]\]")


def _strip_code(text: str) -> str:
    """
    Remove fenced code blocks and inline code spans from `text`.

    Fenced code blocks are removed first (they may contain backticks); inline
    code spans afterwards. The returned string is not valid markdown — its
    only purpose is link extraction.
    """
    without_fenced = _FENCED_CODE_RE.sub("", text)
    return _INLINE_CODE_RE.sub("", without_fenced)


def _extract_canonical_name(text: str) -> str | None:
    """Return the text of the first H2 heading, or None if no H2 is present."""
    match = _H2_RE.search(text)
    if match is None:
        return None
    return match.group("name").strip()


def _is_url(path: str) -> bool:
    """A markdown link path is a URL if it contains a scheme separator `://`."""
    return "://" in path


def _path_basename_slug(path: str) -> str:
    """Strip directory components and the `.md` suffix from a markdown link path."""
    basename = path.rsplit("/", 1)[-1]
    return basename[: -len(".md")]


def extract_md_link_paths(text: str) -> list[str]:
    """
    Return the raw `.md` paths from standard markdown links, in document order.

    Code blocks and inline code spans are excluded. URLs are excluded as well
    — a `https://example.com/foo.md` link is a web reference, not a glossary
    cross-reference. Paths are returned verbatim; basename resolution is the
    caller's job.
    """
    code_stripped = _strip_code(text)
    return [
        match.group(1)
        for match in _MD_LINK_RE.finditer(code_stripped)
        if not _is_url(match.group(1))
    ]


def extract_md_link_paths_with_urls(text: str) -> list[str]:
    """
    Return every `.md` link target verbatim, in document order.

    Unlike `extract_md_link_paths`, URL targets are kept. Callers that walk
    file reachability use this together with `github_url_to_repo_path` so
    that links to the project's own GitHub repository count as internal
    references (the README on PyPI must use absolute URLs to render, but
    those URLs still point at files inside the repo).

    Code blocks and inline code spans are excluded.
    """
    code_stripped = _strip_code(text)
    return [match.group(1) for match in _MD_LINK_RE.finditer(code_stripped)]


# A GitHub blob or raw URL pointing at a file inside a specific repo. Group
# `path` is the in-repo path with the leading ref stripped. Examples that
# match (with repo_url=https://github.com/frankify-app/disambiguate):
#   https://github.com/frankify-app/disambiguate/blob/main/docs/x.md
#   https://raw.githubusercontent.com/frankify-app/disambiguate/main/docs/x.md
_GITHUB_REPO_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)"
    r"/(?:blob|tree|raw)/[^/]+/(?P<path>.+)$"
)
_GITHUB_RAW_URL_RE = re.compile(
    r"^https://raw\.githubusercontent\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)"
    r"/[^/]+/(?P<path>.+)$"
)
_REPO_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?]+?)(?:\.git)?/?$"
)


def github_url_to_repo_path(url: str, repo_url: str) -> str | None:
    """
    Map a GitHub URL to a repo-relative path, or None if it doesn't apply.

    url: the link target as it appears in markdown.
    repo_url: this repository's canonical URL, e.g.
        `https://github.com/frankify-app/disambiguate`.

    Returns
    -------
    The in-repo path (e.g. `docs/glossary/term.md`) when `url` points at a
    file inside `repo_url`. Returns None for any URL that doesn't match the
    `<repo>/blob/<ref>/<path>`, `<repo>/tree/<ref>/<path>`, or
    raw.githubusercontent.com equivalent, or that targets a different repo.

    """
    repo_match = _REPO_URL_RE.match(repo_url)
    if repo_match is None:
        return None
    expected_owner = repo_match.group("owner")
    expected_repo = repo_match.group("repo")

    for regex in (_GITHUB_REPO_URL_RE, _GITHUB_RAW_URL_RE):
        match = regex.match(url)
        if match is None:
            continue
        if match.group("owner") != expected_owner:
            continue
        if match.group("repo") != expected_repo:
            continue
        # Strip a trailing fragment/query; only the path portion is a file.
        path = match.group("path")
        path = path.split("#", 1)[0].split("?", 1)[0]
        return path
    return None


def extract_wikilink_slugs(text: str) -> list[str]:
    """
    Return the slugs of every wiki-style `[[slug]]` link in document order.

    Code blocks and inline code spans are excluded.
    """
    code_stripped = _strip_code(text)
    return [match.group(1) for match in _WIKILINK_RE.finditer(code_stripped)]


def extract_all_link_slugs(text: str) -> list[str]:
    """
    Return the slugs of every cross-reference in document order.

    Both standard markdown links to `.md` files (basename-resolved) and
    wiki-style `[[slug]]` links are collected. URLs and code-block contents
    are excluded. Duplicates are preserved — callers de-duplicate where
    they need to.
    """
    code_stripped = _strip_code(text)

    # Walk both regexes and interleave by document position so duplicates
    # from the two syntaxes appear in source order.
    matches: list[tuple[int, str]] = []
    for match in _MD_LINK_RE.finditer(code_stripped):
        path = match.group(1)
        if _is_url(path):
            continue
        matches.append((match.start(), _path_basename_slug(path)))
    for match in _WIKILINK_RE.finditer(code_stripped):
        matches.append((match.start(), match.group(1)))

    matches.sort(key=lambda pair: pair[0])
    return [slug for _, slug in matches]


def parse_term_text(slug: str, text: str) -> ParsedTerm:
    """
    Parse the contents of a single term file.

    slug: stable identifier, supplied by the caller (typically the file basename).
    text: raw markdown contents.

    Returns
    -------
    ParsedTerm with canonical_name, body, and link_slugs populated.
    canonical_name is None if no H2 heading is found — the lint reports that as
    a fatal error elsewhere; the parser does not raise.

    """
    canonical_name = _extract_canonical_name(text)
    link_slugs = extract_all_link_slugs(text)
    return ParsedTerm(
        slug=slug,
        canonical_name=canonical_name,
        body=text,
        link_slugs=link_slugs,
    )
