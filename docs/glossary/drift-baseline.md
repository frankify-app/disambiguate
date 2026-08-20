## Drift-baseline

A generated, checked-in record of pre-existing [drift](drift.md), so
fatal drift-checks can land on an already-drifted repo without a wall of
suppressions. Findings recorded in the baseline are downgraded to
non-fatal; findings absent from it fail the run.

`disambiguate --drift --write-baseline` regenerates the file
(`.drift-baseline.json`, next to the active `pyproject.toml`, else at the
repo root). Entries are keyed by file, [rule-code](rule-code.md), and
[term](term.md) — never by line number — so they survive unrelated edits
to the same file.

A normal `--drift` run never writes the file. An entry whose finding no
longer occurs is instead reported as a fatal `stale-baseline` finding
naming the regeneration command, so fixing grandfathered drift fails once
until the shrink is committed. The baseline therefore only ever shrinks,
and it shrinks in git rather than in whichever checkout happened to run
the command — a run that rewrote the file in CI would have its shrink
discarded with the runner. This mirrors how a stale
[ignore-hint](ignore-hint.md) is treated: silencing that no longer applies
is itself a finding.
