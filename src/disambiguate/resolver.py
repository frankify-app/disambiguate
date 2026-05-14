"""
Slug resolution against a loaded glossary.

Resolves a set of requested slugs into the topologically-ordered closure of
their dependencies. Topological order is computed via
`graphlib.TopologicalSorter` from the standard library; the sort runs once
over the full induced subgraph of the requested terms plus everything
reachable from them.
"""

from __future__ import annotations

import logging
from graphlib import CycleError as _GraphlibCycleError
from graphlib import TopologicalSorter

from .glossary import Glossary, Term

logger = logging.getLogger(__name__)


class UnknownSlugError(Exception):
    """A requested slug is not present in the glossary."""


class CycleError(Exception):
    """The dependency graph contains a cycle — topological order is impossible."""


def _closure(glossary: Glossary, seeds: list[str]) -> set[str]:
    """
    Return the set of slugs reachable from `seeds` along dependency edges.

    Starts from `seeds` (each must be a known slug) and walks the dependency
    graph, returning every slug encountered including the seeds themselves.
    Raises UnknownSlugError on the first seed not found in the glossary.
    """
    visited: set[str] = set()
    stack: list[str] = []
    for seed in seeds:
        if seed not in glossary.terms:
            raise UnknownSlugError(f"Unknown slug: {seed!r}")
        stack.append(seed)
    while stack:
        slug = stack.pop()
        if slug in visited:
            continue
        visited.add(slug)
        # glossary.dependencies only contains known-slug edges, so every
        # element here exists in glossary.terms.
        stack.extend(glossary.dependencies.get(slug, ()))
    return visited


def resolve(glossary: Glossary, slugs: list[str]) -> list[Term]:
    """
    Return the dependency closure of `slugs` in topological order.

    glossary: loaded glossary.
    slugs: requested term slugs. Empty list means "the entire glossary".

    Returns
    -------
    A list of Term objects ordered so that every term appears after all of
    its dependencies. Each term appears exactly once.

    Raises
    ------
    UnknownSlugError: a requested slug does not exist in the glossary.
    CycleError: the dependency graph contains a cycle.

    """
    if not slugs:
        seeds = list(glossary.terms)
    else:
        seeds = list(slugs)

    closure = _closure(glossary, seeds)

    sorter: TopologicalSorter[str] = TopologicalSorter()
    # Sort dependents alphabetically so the output is stable across runs and
    # platforms regardless of dict insertion order.
    for slug in sorted(closure):
        sorter.add(slug, *sorted(glossary.dependencies.get(slug, set()) & closure))

    try:
        ordered = list(sorter.static_order())
    except _GraphlibCycleError as e:
        raise CycleError(f"Dependency graph contains a cycle: {e}") from e

    logger.debug("resolved %d terms (closure of %s)", len(ordered), seeds)
    return [glossary.terms[slug] for slug in ordered]
