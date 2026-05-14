"""
Lint a glossary against six fatal-on-violation checks.

The checks: cycles, broken cross-references, duplicate slugs, missing H2
headings, invalid slug format, and reachability orphans. Duplicate slugs are
caught by the loader and surface as a `DuplicateSlugError`; the other five
are reported as `LintFinding` objects so the CLI can present all problems
at once instead of stopping on the first.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from graphlib import CycleError as _GraphlibCycleError
from graphlib import TopologicalSorter
from pathlib import Path

from .glossary import Glossary
from .parser import (
    extract_md_link_paths_with_urls,
    extract_wikilink_slugs,
    github_url_to_repo_path,
)

logger = logging.getLogger(__name__)

# Canonical slug format: lowercase letters and digits, with single hyphens
# between segments. No leading/trailing hyphens, no consecutive hyphens.
_CANONICAL_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class LintFinding:
    """
    A single lint violation.

    kind: one of "cycle", "broken-link", "missing-h2", "invalid-slug",
        "orphan". "duplicate-slug" is raised at load time and never
        reaches a finding.
    message: human-readable description, used directly in error output.
    """

    kind: str
    message: str


def _check_cycles(glossary: Glossary) -> list[LintFinding]:
    """Return one finding per cycle detected in the dependency graph."""
    sorter: TopologicalSorter[str] = TopologicalSorter()
    for slug, deps in glossary.dependencies.items():
        sorter.add(slug, *deps)
    try:
        sorter.prepare()
    except _GraphlibCycleError as e:
        detail = e.args[1] if len(e.args) > 1 else e
        return [
            LintFinding(
                kind="cycle",
                message=f"Cycle in dependency graph: {detail}",
            )
        ]
    return []


def _check_broken_links(glossary: Glossary) -> list[LintFinding]:
    """Return one finding per broken cross-reference, deterministic order."""
    findings: list[LintFinding] = []
    for slug in sorted(glossary.broken_links):
        for target in glossary.broken_links[slug]:
            findings.append(
                LintFinding(
                    kind="broken-link",
                    message=(
                        f"{slug}: cross-reference to unknown term "
                        f"{target!r} (no glossary file matches)"
                    ),
                )
            )
    return findings


def _check_missing_h2(glossary: Glossary) -> list[LintFinding]:
    """Return one finding per term file lacking an H2 heading."""
    findings: list[LintFinding] = []
    for slug in sorted(glossary.terms):
        term = glossary.terms[slug]
        if term.canonical_name is None:
            findings.append(
                LintFinding(
                    kind="missing-h2",
                    message=f"{slug}: missing required H2 heading in {term.path}",
                )
            )
    return findings


def _check_slug_format(glossary: Glossary) -> list[LintFinding]:
    """Return one finding per slug not matching the canonical slug format."""
    findings: list[LintFinding] = []
    for slug in sorted(glossary.terms):
        if _CANONICAL_SLUG.fullmatch(slug):
            continue
        findings.append(
            LintFinding(
                kind="invalid-slug",
                message=(
                    f"{slug}: slug does not match canonical format "
                    f"(lowercase letters, digits, and single hyphens "
                    f"between segments; no leading or trailing hyphen)"
                ),
            )
        )
    return findings


def _walk_reachable(
    roots: Iterable[Path],
    glossary: Glossary,
    repo_root: Path | None = None,
    repo_url: str | None = None,
) -> set[Path]:
    """
    Return the set of `.md` file paths reachable from `roots` by link.

    Walks both glossary terms and external markdown documents. Cycles are
    handled by the visited-set check, not by topological sort. Non-`.md`
    links are ignored. URLs are ignored unless `repo_url` is provided and
    they point at a file inside that repository (a `<repo>/blob/<ref>/<path>`
    or raw equivalent) — those resolve against `repo_root` exactly like
    relative links, so the README on PyPI can use absolute GitHub URLs and
    those links still count as internal cross-references.
    """
    visited: set[Path] = set()
    queue: list[Path] = []
    for root in roots:
        resolved = root.resolve()
        if resolved not in visited:
            queue.append(resolved)

    # Cache slug -> term path for wikilink and basename-fallback resolution.
    slug_to_path: dict[str, Path] = {
        slug: term.path.resolve() for slug, term in glossary.terms.items()
    }

    while queue:
        current = queue.pop()
        if current in visited:
            continue
        visited.add(current)
        try:
            text = current.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("could not read %s during reachability walk: %s", current, e)
            continue

        for raw_path in extract_md_link_paths_with_urls(text):
            if "://" in raw_path:
                # URLs only count as internal references when they point at
                # this repo's own GitHub blob/tree (or raw.githubusercontent)
                # URL. Anything else is treated as a true external link and
                # skipped.
                if repo_url is None or repo_root is None:
                    continue
                repo_path = github_url_to_repo_path(raw_path, repo_url)
                if repo_path is None:
                    continue
                target_path = (repo_root / repo_path).resolve()
                if target_path.is_file() and target_path not in visited:
                    queue.append(target_path)
                continue

            target_path = (current.parent / raw_path).resolve()
            if target_path.is_file() and target_path not in visited:
                queue.append(target_path)
            else:
                # Path-relative resolution failed; fall back to basename
                # resolution against glossary slugs. Covers the case where
                # an external doc writes `[term](term.md)` from a directory
                # that doesn't actually contain the file.
                basename = raw_path.rsplit("/", 1)[-1]
                slug = basename[: -len(".md")] if basename.endswith(".md") else basename
                fallback = slug_to_path.get(slug)
                if fallback is not None and fallback not in visited:
                    queue.append(fallback)

        for slug in extract_wikilink_slugs(text):
            target = slug_to_path.get(slug)
            if target is not None and target not in visited:
                queue.append(target)

    return visited


def _check_orphans(
    glossary: Glossary,
    roots: list[Path],
    repo_root: Path | None = None,
    repo_url: str | None = None,
) -> list[LintFinding]:
    """Return one finding listing every term not reachable from `roots`."""
    visited = _walk_reachable(roots, glossary, repo_root=repo_root, repo_url=repo_url)
    orphan_slugs = sorted(
        slug
        for slug, term in glossary.terms.items()
        if term.path.resolve() not in visited
    )
    if not orphan_slugs:
        return []

    root_names = ", ".join(p.name for p in roots) or "(none)"
    bullets = "\n".join(f"  - {slug}" for slug in orphan_slugs)
    message = (
        f"Orphan terms found (not reachable from roots: {root_names}):\n"
        f"{bullets}\n"
        f"\nOrphans must be reachable from at least one root via markdown links.\n"
        f"Add links from a root document, or override roots with `--roots <files>`\n"
        f"or `DISAMBIGUATE_ROOTS=...`."
    )
    return [LintFinding(kind="orphan", message=message)]


def lint_glossary(
    glossary: Glossary,
    roots: list[Path],
    repo_root: Path | None = None,
    repo_url: str | None = None,
) -> list[LintFinding]:
    """
    Run every lint check against `glossary` and return the combined findings.

    glossary: loaded glossary.
    roots: documents from which reachability is measured. Caller is
        responsible for resolving the roots (flag, env, default).
    repo_root: directory used to resolve in-repo GitHub URLs to local files
        during reachability. When None, GitHub URLs are skipped.
    repo_url: the canonical repository URL (e.g.
        `https://github.com/owner/name`). When supplied alongside
        `repo_root`, absolute links to this repo on github.com count as
        internal references during the orphan walk.

    Returns
    -------
    A list of LintFinding objects; empty list means clean. Order is
    deterministic: cycles, broken-links, missing-h2, invalid-slug, orphans.

    """
    findings: list[LintFinding] = []
    findings.extend(_check_cycles(glossary))
    findings.extend(_check_broken_links(glossary))
    findings.extend(_check_missing_h2(glossary))
    findings.extend(_check_slug_format(glossary))
    findings.extend(
        _check_orphans(glossary, roots, repo_root=repo_root, repo_url=repo_url)
    )
    return findings
