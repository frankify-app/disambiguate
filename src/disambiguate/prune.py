"""
Remove glossary terms that nothing links.

A repo can acquire terms it does not link. Those are `orphan` findings,
so `--lint` fails on a repo that did nothing wrong. Exempting them
would make "unlinked" a legitimate state and blunt the check for
everyone; removing them instead keeps the check's teeth and lets the
repo converge to exactly the terms it links.

Removal is consent-based: a term opts in with the `auto-prune`
annotation. `--all-orphans` widens the scope to orphans that never
opted in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from disambiguate.glossary import Glossary
from disambiguate.lint import orphan_slugs


@dataclass(frozen=True)
class PrunePlan:
    """
    What a prune run would remove.

    remove: slugs to remove now — orphaned, and consenting unless the
        caller widened the scope.
    additional: slugs `--all-orphans` would remove on top of `remove`;
        empty when the scope is already widened.
    """

    remove: list[str] = field(default_factory=list)
    additional: list[str] = field(default_factory=list)


def plan_prune(
    glossary: Glossary,
    roots: list[Path],
    *,
    all_orphans: bool = False,
) -> PrunePlan:
    """
    Decide which terms a prune run removes.

    glossary: the loaded glossary.
    roots: documents reachability is measured from.
    all_orphans: also remove orphans that never declared consent.

    Returns
    -------
    A PrunePlan. Pure — reads the graph, touches no files.

    """
    orphans = orphan_slugs(glossary, roots)
    if all_orphans:
        return PrunePlan(remove=list(orphans), additional=[])

    # DECISION: single pass, not a fixpoint loop. Orphanhood is
    # reachability from the roots, so a reachable term's whole path is
    # reachable too — removing orphans can never orphan a term the roots
    # still reach. The orphan set is already its own fixpoint, which
    # settles the question #52 left open.
    remove = [slug for slug in orphans if glossary.terms[slug].auto_prune]
    additional = [slug for slug in orphans if slug not in set(remove)]
    return PrunePlan(remove=remove, additional=additional)
