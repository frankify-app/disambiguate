"""
Extract glossary-shaped slug references from an arbitrary markdown document.

Used by `--from`. A reference is glossary-shaped if it is either a wiki-link
or a markdown link to a `.md` file. Non-`.md` links are silently ignored;
glossary-shaped links whose basename does not match any known slug are an
error so the user notices broken references in their prose.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .glossary import Glossary
from .parser import extract_all_link_refs

logger = logging.getLogger(__name__)


class BrokenFromLinkError(Exception):
    """A glossary-shaped link in the source document references an unknown slug."""


def extract_slugs(
    text: str, glossary: Glossary, source_path: Path | None = None
) -> list[str]:
    """
    Return the slugs referenced by `text`, preserving order, without duplicates.

    text: a markdown document.
    glossary: the active glossary; used to validate slugs and to distinguish
        glossary-shaped links from arbitrary `.md` links.
    source_path: filesystem location of `text`, when it has one. Enables
        resolve-then-classify: a `.md` link whose basename is no glossary
        slug is a document link, not a broken reference, when its path
        resolves to an existing file relative to the source document —
        the same classification the lint reachability walk applies. None
        (e.g. stdin) keeps basename-only classification.

    Returns
    -------
    A list of glossary slugs in first-occurrence order.

    Raises
    ------
    BrokenFromLinkError: a glossary-shaped link references an unknown slug.
        Non-glossary links (external URLs, image paths, non-`.md`) are ignored.

    A glossary-shaped link is any `[text](path/to/foo.md)` or `[[foo]]` whose
    basename matches a slug in the glossary. A `.md` link whose basename does
    NOT match a slug is the broken case — fail loud, do not silently drop.

    """
    seen: set[str] = set()
    ordered: list[str] = []
    broken: list[str] = []

    for slug, path in extract_all_link_refs(text):
        if slug in glossary.terms:
            if slug not in seen:
                seen.add(slug)
                ordered.append(slug)
        elif source_path is None or path is None:
            # No base path to resolve against (stdin), or a wikilink —
            # wikilinks address terms by slug and carry no filesystem
            # path, so basename-only classification is all there is.
            broken.append(slug)
        elif not (source_path.parent / path).is_file():
            broken.append(slug)

    if broken:
        raise BrokenFromLinkError(
            f"Glossary-shaped links reference unknown slugs: {sorted(set(broken))}"
        )
    return ordered
