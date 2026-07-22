"""
Drift-check engine: detect prose drifting from the glossary.

Drift-checks walk the same reachable corpus as the reachability lint and
report, per rule-code, places where prose usage diverges from the
glossary's canonical form. They are fatal by default and surfaced through
the CLI's `--drift` mode, kept separate from the deterministic `--lint`
checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .glossary import Glossary


@dataclass(frozen=True)
class DriftFinding:
    """
    A single drift violation.

    rule_code: stable identifier of the drift-check, e.g. "unlinked-term".
    path: document the drift occurs in.
    line: 1-based line of the offending term-mention.
    term: slug of the glossary term the finding is about.
    message: human-readable description, used directly in error output.
    """

    rule_code: str
    path: Path
    line: int
    term: str
    message: str


def run_drift_checks(glossary: Glossary, roots: list[Path]) -> list[DriftFinding]:
    """
    Run every drift-check over the corpus reachable from `roots`.

    glossary: loaded glossary.
    roots: documents from which the corpus walk starts.

    Returns
    -------
    A list of DriftFinding objects; empty list means no drift.

    """
    raise NotImplementedError
