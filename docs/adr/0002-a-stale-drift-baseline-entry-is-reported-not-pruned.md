# A stale drift-baseline entry is reported, not pruned

Ticket #37 left the prune mechanism open: a drift-baseline entry whose
finding no longer occurs could be pruned automatically or reported.
Auto-prune shipped first, and was wrong. It made `--drift` — a check, and
otherwise read-only — rewrite a tracked file as a side effect, and it put
the rewrite in whichever checkout happened to run the command. In CI that
is the runner's, discarded with the job, so the baseline never shrank
where it lasts. The ratchet only tightened when a developer ran the
command locally, noticed the modified file, and committed it.

Decision: a normal run never writes. A stale entry is a fatal
`stale-baseline` finding naming `--drift --write-baseline` as the remedy.
Fixing grandfathered drift therefore fails once, with a mechanical
one-command fix whose result lands in a commit.

This mirrors the treatment of a stale [ignore-hint](../glossary/ignore-hint.md),
which the same mode already reports as a fatal `stale-suppression`
finding on identical reasoning: silencing that no longer applies should be
caught loudly, not repaired invisibly. Handling the two opposite ways in
one feature was the inconsistency that surfaced this.

The accepted cost: a doc change on the default branch can strand a
baseline entry and turn an unrelated pull request red. The failure is
mechanical and self-describing, which is the trade we are making — a
build that fails with the fix in the message, over a baseline that
silently keeps excusing drift that has already been fixed.
