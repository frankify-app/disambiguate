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

from .glossary import Glossary, Term
from .lint import walk_reachable
from .mentions import find_mentions
from .parser import extract_all_link_slugs
from .suppressions import (
    DriftConfig,
    inline_hint_covers,
    parse_file_hints,
    parse_inline_hints,
)


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


def _term_variants(term: Term) -> list[str]:
    """Return the spellings that count as a mention of `term`."""
    variants = [term.slug]
    if term.canonical_name is not None:
        variants.append(term.canonical_name)
    return variants


def _check_unlinked_terms(
    glossary: Glossary, corpus: dict[Path, str]
) -> list[DriftFinding]:
    """
    Report each (document, term) pair mentioned in prose but never linked.

    A single link to the term anywhere in the document satisfies the rule
    for every mention in that document. A term is never checked against its
    own defining file — a definition necessarily names itself.
    """
    findings: list[DriftFinding] = []
    for path in sorted(corpus):
        text = corpus[path]
        linked_slugs = set(extract_all_link_slugs(text))
        for slug in sorted(glossary.terms):
            term = glossary.terms[slug]
            if path == term.path.resolve():
                continue
            if slug in linked_slugs:
                continue
            mentions = find_mentions(text, _term_variants(term))
            if not mentions:
                continue
            first = mentions[0]
            findings.append(
                DriftFinding(
                    rule_code="unlinked-term",
                    path=path,
                    line=first.line,
                    term=slug,
                    message=(
                        f"{first.matched!r} is mentioned but never linked in "
                        f"this document; link the term once, e.g. "
                        f"[{first.matched}]({slug}.md)"
                    ),
                )
            )
    return findings


def _read_corpus(glossary: Glossary, roots: list[Path]) -> dict[Path, str]:
    """Read every document reachable from `roots` into memory, keyed by path."""
    corpus: dict[Path, str] = {}
    for path in walk_reachable(roots, glossary):
        corpus[path] = path.read_text(encoding="utf-8")
    return corpus


def run_drift_checks(
    glossary: Glossary,
    roots: list[Path],
    config: DriftConfig | None = None,
) -> list[DriftFinding]:
    """
    Run every drift-check over the corpus reachable from `roots`.

    glossary: loaded glossary.
    roots: documents from which the corpus walk starts.
    config: config-level suppression settings, or None for none.

    Returns
    -------
    A list of DriftFinding objects; empty list means no drift. Order is
    deterministic: by document path, then rule-code order per document.

    """
    corpus = _read_corpus(glossary, roots)
    raw_findings = _check_unlinked_terms(glossary, corpus)
    return _apply_suppressions(raw_findings, corpus, config)


def _apply_suppressions(
    findings: list[DriftFinding],
    corpus: dict[Path, str],
    config: DriftConfig | None = None,
) -> list[DriftFinding]:
    """Drop findings covered by a config ignore or an ignore-hint."""
    inline_by_path = {path: parse_inline_hints(text) for path, text in corpus.items()}
    file_rules_by_path = {
        path: {hint.rule_code for hint in parse_file_hints(text)}
        for path, text in corpus.items()
    }
    kept: list[DriftFinding] = []
    for finding in findings:
        if config is not None and config.covers(finding.rule_code, finding.path):
            continue
        if finding.rule_code in file_rules_by_path.get(finding.path, set()):
            continue
        hints = inline_by_path.get(finding.path, [])
        if any(
            inline_hint_covers(hint, finding.rule_code, finding.line, finding.term)
            for hint in hints
        ):
            continue
        kept.append(finding)
    return kept
