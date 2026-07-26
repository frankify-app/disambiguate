"""
Load a directory of term files into an in-memory glossary.

The glossary is the unit Disambiguate operates on: a directory of `*.md`
files (recursively), one term per file, addressed by basename. Duplicate
basenames are an error.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .parser import parse_term_text

logger = logging.getLogger(__name__)


class DuplicateSlugError(Exception):
    """Two term files share a basename — slugs must be unique."""


@dataclass(frozen=True)
class Term:
    """
    A single loaded term.

    slug: stable identifier (file basename without `.md`).
    canonical_name: text of the first H2 heading, or None if missing.
        Missing H2s are reported by the lint, not raised here.
    body: the full original markdown text of the file.
    link_slugs: cross-reference targets in document order; may include
        unknown slugs (those are surfaced by lint, not filtered out here).
    path: absolute path to the source file on disk.
    auto_prune: the term declares that it may be removed once nothing
        links it. Absent marker means no consent.
    """

    slug: str
    canonical_name: str | None
    body: str
    link_slugs: list[str]
    path: Path
    auto_prune: bool = False


@dataclass(frozen=True)
class Glossary:
    """
    A loaded glossary directory.

    root: the directory the glossary was loaded from.
    terms: slug -> Term, one entry per file.
    dependencies: slug -> set of slugs the term depends on, restricted to
        slugs that actually exist in the glossary. Used to feed the
        topological sorter without forcing it to error on broken links —
        the lint reports those separately.
    broken_links: slug -> list of cross-reference targets that are not
        present as terms in the glossary. Order-preserving, duplicates kept.
    """

    root: Path
    terms: dict[str, Term]
    dependencies: dict[str, set[str]] = field(default_factory=dict)
    broken_links: dict[str, list[str]] = field(default_factory=dict)


def load_glossary(root: Path) -> Glossary:
    """
    Load every `*.md` file under `root` recursively into a Glossary.

    root: directory containing term files.

    Returns
    -------
    A Glossary with terms, the dependency graph (known links only), and
    per-term broken-link lists (unknown links).

    Raises
    ------
    DuplicateSlugError: two files share a basename.
    FileNotFoundError: `root` does not exist.

    """
    if not root.is_dir():
        raise FileNotFoundError(f"Glossary directory not found: {root}")

    terms: dict[str, Term] = {}
    seen_paths: dict[str, Path] = {}
    for md_path in sorted(root.rglob("*.md")):
        slug = md_path.stem
        if slug in seen_paths:
            existing = seen_paths[slug]
            raise DuplicateSlugError(
                f"Duplicate slug {slug!r}: {existing} and {md_path}"
            )
        seen_paths[slug] = md_path
        text = md_path.read_text(encoding="utf-8")
        parsed = parse_term_text(slug, text)
        terms[slug] = Term(
            slug=parsed.slug,
            canonical_name=parsed.canonical_name,
            body=parsed.body,
            link_slugs=parsed.link_slugs,
            path=md_path,
            auto_prune=parsed.auto_prune,
        )
        logger.debug("loaded term %s from %s", slug, md_path)

    dependencies: dict[str, set[str]] = {}
    broken_links: dict[str, list[str]] = {}
    for slug, term in terms.items():
        deps: set[str] = set()
        broken: list[str] = []
        for target in term.link_slugs:
            if target == slug:
                # Self-references would create trivial cycles. They are not
                # meaningful — a term cannot define itself before itself.
                continue
            if target in terms:
                deps.add(target)
            else:
                broken.append(target)
        dependencies[slug] = deps
        if broken:
            broken_links[slug] = broken

    logger.info("loaded %d terms from %s", len(terms), root)
    return Glossary(
        root=root,
        terms=terms,
        dependencies=dependencies,
        broken_links=broken_links,
    )
