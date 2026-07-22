"""
Suppression surfaces for drift-checks.

Three ways to silence a drift finding, coarsest first:

- config-level ignore: a rule-code disabled repo-wide (optionally per
  path) under `[tool.disambiguate]`.
- file-level opt-out: an ignore-hint disabling a rule-code for the whole
  document, e.g. `<!-- d10e: ignore-file[unlinked-term] -->`.
- inline ignore-hint: an HTML comment on the finding's line or the line
  directly above, e.g. `<!-- d10e: ignore[unlinked-term] widget -->`.

Hints live inside HTML comments so they are invisible in rendered
markdown. The hint keyword is `d10e` (numeronym of `disambiguate`);
`disambiguate` is accepted as a long-form alias.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# One regex per hint form. The keyword is `d10e` or `disambiguate`; the
# rule-code is bracketed; an inline hint may carry a target term after the
# brackets.
_INLINE_HINT_RE = re.compile(
    r"<!--\s*(?:d10e|disambiguate):\s*ignore\[(?P<rule>[a-z0-9-]+)\]"
    r"(?:\s+(?P<target>[^>\s]+))?\s*-->"
)


@dataclass(frozen=True)
class InlineHint:
    """
    One inline ignore-hint parsed from a document.

    line: 1-based line the hint sits on. The hint suppresses findings on
        this line and the line directly below (hint-above placement).
    rule_code: the rule-code the hint silences.
    target: term slug the hint is scoped to, or None for any term.
    """

    line: int
    rule_code: str
    target: str | None


def parse_inline_hints(text: str) -> list[InlineHint]:
    """
    Parse every inline ignore-hint in `text`, in document order.

    text: full markdown source of a document.

    Returns
    -------
    A list of InlineHint objects; empty list when the document carries no
    hints.

    """
    hints: list[InlineHint] = []
    for match in _INLINE_HINT_RE.finditer(text):
        line = 1 + text.count("\n", 0, match.start())
        hints.append(
            InlineHint(
                line=line,
                rule_code=match.group("rule"),
                target=match.group("target"),
            )
        )
    return hints


def inline_hint_covers(hint: InlineHint, rule_code: str, line: int, term: str) -> bool:
    """
    Return True when `hint` suppresses a finding of `rule_code` at `line`.

    A hint covers its own line and the line directly below it. A hint with
    a target only covers findings about that term.
    """
    if hint.rule_code != rule_code:
        return False
    if line not in (hint.line, hint.line + 1):
        return False
    return hint.target is None or hint.target == term
