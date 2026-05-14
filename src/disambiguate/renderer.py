"""
Render an ordered list of terms to a single markdown string.

Term bodies are concatenated as-is with a blank-line separator. The renderer
does not modify cross-references or rewrite headings — what is in the source
file is what comes out.
"""

from __future__ import annotations

import logging
import shlex
from collections.abc import Iterable

from .glossary import Term

logger = logging.getLogger(__name__)

_SEPARATOR = "\n\n"


def render_terms(terms: Iterable[Term], preamble: str = "") -> str:
    """
    Render `terms` to markdown.

    terms: ordered iterable of Term objects.
    preamble: prepended verbatim. Caller is responsible for trailing
        whitespace; nothing is added.

    Returns
    -------
    A single string suitable for printing to stdout.

    """
    chunks: list[str] = []
    if preamble:
        chunks.append(preamble)
    for term in terms:
        body = term.body
        # Normalize trailing whitespace so the separator behaves the same
        # regardless of whether the source file ended with a newline.
        chunks.append(body.rstrip("\n"))
    return _SEPARATOR.join(chunks) + "\n"


def build_explain_preamble(terms: list[str]) -> str:
    """
    Build the preamble that `--explain` prepends to its output.

    terms: the slugs the user passed to `--explain`. Empty means "render
        everything".

    Returns
    -------
    The preamble, with the literal example invocation that produced this
    output and a horizontal rule separator at the end.

    """
    quoted = " ".join(shlex.quote(t) for t in terms)
    example = "disambiguate" + (f" {quoted}" if quoted else "")
    preamble = "\n".join(
        [
            "What follows is rendered from Disambiguate's own bundled glossary, ",
            f"equivalent to running `{example}` against it. Read it both as the ",
            "canonical definition of Disambiguate's vocabulary and as the ",
            "reference example of how to author a Disambiguate-compatible ",
            "glossary. Output is in topological order — read top to bottom, ",
            "nothing will be undefined when you encounter it.",
            "",
            "---",
        ]
    )
    return f"{preamble}\n\n"
