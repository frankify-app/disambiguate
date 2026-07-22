"""
Term-mention matching: find occurrences of a term's name in prose.

A term-mention is an occurrence of a term's canonical name or slug (or an
avoided-term) in a document's prose. Matching is case-insensitive and
word-boundaried, where a hyphen counts as a word character: `term` does not
match inside `unlinked-term`, so a mention of a compound term never doubles
as a mention of its parts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Mention:
    """
    One matched term-mention in a document.

    offset: 0-based character offset of the match start.
    line: 1-based line number of the match start.
    matched: the exact text as it appears in the document.
    """

    offset: int
    line: int
    matched: str


def _variant_pattern(variants: list[str]) -> re.Pattern[str]:
    """
    Compile a case-insensitive pattern matching any of `variants` whole.

    Boundaries treat `[A-Za-z0-9-]` as word characters, so a variant never
    matches inside a larger word or a larger hyphenated compound.
    """
    alternation = "|".join(
        re.escape(v) for v in sorted(variants, key=len, reverse=True)
    )
    return re.compile(
        rf"(?<![A-Za-z0-9-])(?:{alternation})(?![A-Za-z0-9-])",
        re.IGNORECASE,
    )


def find_mentions(text: str, variants: list[str]) -> list[Mention]:
    """
    Find every mention of any variant in `text`, in document order.

    text: full markdown source of a document.
    variants: non-empty spellings to match (canonical name, slug, ...).

    Returns
    -------
    A list of Mention objects ordered by offset; empty list when nothing
    matches.

    """
    pattern = _variant_pattern([v for v in variants if v])
    mentions: list[Mention] = []
    for match in pattern.finditer(text):
        line = 1 + text.count("\n", 0, match.start())
        mentions.append(
            Mention(offset=match.start(), line=line, matched=match.group(0))
        )
    return mentions
