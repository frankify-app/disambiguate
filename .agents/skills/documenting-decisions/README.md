# Agent Instructions for Checkpoint Awareness

These are deliberately minimal — per the ETH Zurich AGENTbench study, verbose instruction files increase agent step count and cost without improving outcomes. Include only what the agent cannot infer from the codebase itself.

## Combining blocks

Pick the minimal version plus whichever additional blocks match your risk profile. A typical combination for a web app with auth:

1. decision-markers.md (always)
2. pre-approval-gate.md (if tasks are large or loosely specified)
3. security-hardening.md (if auth/payments/user data exist)
4. irreversibility-protection.md (if the agent has DB access)

Resist the urge to add all blocks. Each instruction the agent reads adds steps and cost. Start minimal, add rules only after you observe a failure mode that the rule would have prevented.

If using the CODER/REVIEWER/TESTER subagent architecture:

```markdown
## Review protocol

CODER: When making noteworthy decisions during implementation, annotate them
inline with DECISION:<CATEGORY> markers. After completing the task, generate
DECISION_LOG.md from all markers in changed files.

REVIEWER: Verify decision markers against the actual diff:

- Every checkpoint-category change in the diff has a corresponding DECISION: marker
- No DECISION: markers reference code that doesn't exist
- Run: git diff origin/main --name-only | xargs grep -n "DECISION:" 2>/dev/null
- Flag any unlogged checkpoint changes as "UNLOGGED: [category] — [description]"
- If UNLOGGED items exist, the PR should not auto-merge regardless of test results

TESTER: Verify that tests exist for any DECISION:IFACE changes and that
DECISION:SEC changes have corresponding security test cases.
```
