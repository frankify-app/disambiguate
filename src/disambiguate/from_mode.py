"""
Extract glossary-shaped slug references from an arbitrary markdown document.

Used by `--from`. A reference is glossary-shaped if it is either a wiki-link
or a markdown link to a `.md` file. Non-`.md` links are silently ignored;
glossary-shaped links whose basename does not match any known slug are an
error so the user notices broken references in their prose.
"""

from __future__ import annotations

import logging

from .glossary import Glossary
from .parser import extract_all_link_slugs

logger = logging.getLogger(__name__)


class BrokenFromLinkError(Exception):
    """A glossary-shaped link in the source document references an unknown slug."""


def extract_slugs(text: str, glossary: Glossary) -> list[str]:
    """
    Return the slugs referenced by `text`, preserving order, without duplicates.

    text: a markdown document.
    glossary: the active glossary; used to validate slugs and to distinguish
        glossary-shaped links from arbitrary `.md` links.

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

    for slug in extract_all_link_slugs(text):
        if slug in glossary.terms:
            if slug not in seen:
                seen.add(slug)
                ordered.append(slug)
        else:
            broken.append(slug)

    if broken:
        raise BrokenFromLinkError(
            f"Glossary-shaped links reference unknown slugs: {sorted(set(broken))}"
        )
    return ordered
