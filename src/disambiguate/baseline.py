"""
Drift-baseline: a checked-in record of pre-existing drift.

Adopting fatal drift-checks on an already-drifted repo would need a wall
of suppressions. Instead, a generated baseline records the currently-known
findings; findings present in the baseline are non-fatal, findings absent
from it fail the run. The baseline only shrinks under normal work: entries
whose finding no longer occurs are pruned automatically so the baseline
does not rot.

Entries are keyed by (path, rule-code, term) — never by line number — so
they survive unrelated edits to the same file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .drift import DriftFinding

BASELINE_VERSION = 1
BASELINE_FILENAME = ".drift-baseline.json"


@dataclass(frozen=True)
class Baseline:
    """
    A loaded drift-baseline.

    path: file the baseline was loaded from; entry paths are relative to
        its parent directory.
    keys: the grandfathered finding keys, each "path:rule-code:term" with
        path in posix form relative to the baseline directory.
    """

    path: Path
    keys: frozenset[str]


def finding_key(finding: DriftFinding, root: Path) -> str:
    """
    Return the baseline key for `finding`, with its path relative to `root`.

    finding: the drift finding to key.
    root: directory baseline entry paths are relative to.

    Returns
    -------
    A "path:rule-code:term" string; the path falls back to its absolute
    posix form when it is outside `root`.

    """
    raise NotImplementedError


def save_baseline(path: Path, findings: list[DriftFinding]) -> None:
    """
    Write a baseline capturing `findings` to `path` as JSON.

    path: baseline file location; entry paths are stored relative to its
        parent directory.
    findings: the findings to grandfather.
    """
    raise NotImplementedError


def load_baseline(path: Path) -> Baseline | None:
    """
    Load a baseline from `path`.

    path: baseline file location.

    Returns
    -------
    The Baseline, or None when `path` does not exist.

    """
    raise NotImplementedError


def apply_baseline(
    findings: list[DriftFinding], baseline: Baseline
) -> tuple[list[DriftFinding], list[str]]:
    """
    Split `findings` against `baseline`.

    findings: post-suppression findings from the current run.
    baseline: the loaded baseline.

    Returns
    -------
    A pair (fresh, stale_keys): `fresh` are findings absent from the
    baseline (still fatal); `stale_keys` are baseline keys no finding
    matched anymore (prunable).

    """
    raise NotImplementedError
