# Disambiguate — Agent Guidelines

Repo: https://github.com/frankify-app/disambiguate

## Project Specifics

### Terminology

Ubiquitous language is defined in docs/glossary/.

### Architecture

Read [docs/architecture.md](docs/architecture.md) before touching touching any code.

## Rules

- Small, single-purpose files
- Readability over brevity — straightforward, easy-to-follow code. No compact "one-liners" stretching across multiple lines (e.g. nested ternaries). Stretching across multiple lines is only allowed if it aids readability.
- All routes and non-trivial functions: docstring contracts (params, returns, errors)
- Test cases cover edge cases and every `@returns` line

### Errors

- Forward all errors with full detail + variable values, never swallow or catch, let exceptions propagate with their full traceback to make proper debugging possible
- Never catch exceptions if tfhey are actual errors that can't be handled
- Include relevant variable values in error messages, e.g.:
  `"Failed to fetch peers for workspace_id=${workspace_id}: ${e}"`

## Skills

Live in `.agents/skills/`. Synced externally — don't edit skill files, add repo-local overrides in AGENTS.md
1% rule: if skill might apply, load it.

**Loading:** Use platform skill tool if available, else read `.agents/skills/<name>/SKILL.md` directly. (This overrides the "Never use the Read tool on skill files" rule in `using-superpowers` — that rule assumed all skills would be registered with the harness, which isn't true on every platform.)

| Skill                            | Trigger                                             |
| -------------------------------- | --------------------------------------------------- |
| `using-superpowers`              | Every session — read first                          |
| `test-driven-development`        | Any implementation task                             |
| `documenting-decisions`          | Any implementation task — place `DECISION:` markers |
| `requesting-code-review`         | After completing implementation                     |
| `finishing-a-development-branch` | Once GitHub issue fully implemented and tested      |

## Git

- Branch: `<agent>/<issue-number>-<desc>` (e.g. `hermes/42-fix-auth`, `claude/42-fix-auth`)
- Never push to `main`
- Create PR immediately on branch creation via `gh pr create`
- Commits: conventional commits
- Document unexpected encounters and design decisions in commit message as well as PR/Issue

## Workflow

Stop between each step — wait for user review unless explicitly told otherwise:

1. **Plan** — Read issue, explore codebase, write plan. Flag `DECISION:SCOPE` if resolving ambiguities.
   -> SKILL `documenting-decisions` references: `pre-approval-gate.md`, `scope-interpretation.md`.

2. **Tests** — Follow `test-driven-development`
3. **Implement** — Minimal code to pass tests. Once tests pass, implement remaining code according to ticket spec. Place `DECISION:` markers per `documenting-decisions` skill.
   -> SKILL `documenting-decisions` references: `decision-markers.md`, `marker-examples.md`.
4. **Code review** — Run `requesting-code-review`, fix Critical/Important
5. **Finish** — Run `finishing-a-development-branch`

Every commit: `make check` first. One commit per logical unit. TDD red-step commits (failing tests, passing lint) required.

Don't fix lint manually — run formatter. Only touch code if tools can't resolve.

**PR description** — PR body must include:

- `Closes #<number>`.
- Add all obstacles that did not go according to your initial plan and in the extremely rare event where spec deviation was unavoidable.
- Add all `DECISION:` markers from diff to PR body.

## Commands

`make <cmd>`: `check`, `test`, `unit-test`, `lint`, `mypy`, `auto-format`, `install`, `main`, `run`, `help`

## Dependencies

`uv add <package>` only. Never edit pyproject/requirements directly.

## Documentation

- All non-trivial functions must have contracts in the function doc string
- Document all params, return shapes, and every possible error response
- Test cases must cover edge cases for inputs and every @returns line in the contract
- Non-trivial decisions or behavior should be documented via inline comments
