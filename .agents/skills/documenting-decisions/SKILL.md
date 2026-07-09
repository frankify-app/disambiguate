---
name: documenting-decisions
description: Routes human attention to decisions that matter in agent-generated code. Active during planning, implementing, fixing. Defines when and how to place DECISION markers in code comments. Also applies when reviewing a diff/PR on request.
---

# Documenting Decisions

## Checkpoint tags

| Tag     | When to mark                                                                                          |
| ------- | ----------------------------------------------------------------------------------------------------- |
| `ARCH`  | New abstractions, deps, data models, component boundaries — anything that shapes long-term structure. |
| `SCOPE` | You resolved an ambiguity in the task by choosing an interpretation.                                  |
| `IFACE` | Changed a public API, config schema, CLI flag, env var, or wire format.                               |
| `SEC`   | Touched auth, crypto, permissions, network exposure, or input validation.                             |
| `IRREV` | Created a migration, data deletion, deployment trigger, or external side effect.                      |
| `NOVEL` | No existing repo pattern to follow — you interpolated from training data.                             |

Do not mark routine changes (pattern-following, boilerplate, refactoring).

## Format

See this skill's `references/` `decision-markers.md` and (if needed) `marker-examples.md`.

## After task completion

Generate decision log from markers in changed files and add to PR description:

```markdown
## Decisions requiring review
- **TAG** `file:line` — explanation
## Routine (skip review)
[One-line summary]
```

## Diff classification mode

When user requests review of diff, classify each hunk as one of the six tags or `ROUTINE`. Present as `File: path — TAG` with line ranges.

## Reference files

- `references/canary-signals.md` — CI scripts for automated checkpoint detection (repo setup, not runtime).
- `references/marker-examples.md` — example markers in multiple languages.
- other files in references are only relevant if explicitly mentioned in AGENTS.md or requested by the user.
