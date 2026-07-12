# Disambiguate — Agent Guidelines

Repo: <https://github.com/frankify-app/disambiguate>

## Project Specifics

### Terminology

Ubiquitous language is defined in docs/glossary/. Use

```bash
uvx disambiguate <term>
```

to get a topologically ordered glossary disambiguating all relevant terms
to understand the given term.

Before working on a ticket, run:

```bash
uvx disambiguate --from <ticket-file>
```

or for GitHub issues:

```bash
ghx issue view <number> --json body -q .body | uvx disambiguate --from -
```

to resolve all referenced terms at once.

### Architecture

Read [docs/architecture.md](docs/architecture.md) before touching any code.

## Rules

- Small, single-purpose files
- Readability over brevity — straightforward, easy-to-follow code. No compact "one-liners" stretching across multiple lines (e.g. nested ternaries). Stretching across multiple lines is only allowed if it aids readability.
- All routes and non-trivial functions: docstring contracts (params, returns, errors)
- Test cases cover edge cases and every `@returns` line

### Errors

- Forward all errors with full detail + variable values, never swallow or catch, let exceptions propagate with their full traceback to make proper debugging possible
- Never catch exceptions if they are actual errors that can't be handled
- Include relevant variable values in error messages, e.g. for JS/TS:
  `"Failed to fetch peers for workspace_id=${workspace_id}: ${e}"`

## Skills

Live in `.agents/skills/`. Synced using `npx skills update -p -y` — don't edit skill files, add repo-local overrides in AGENTS.md
1% rule: if skill might apply, load it.

**Loading:** Use platform skill tool if available, else read `.agents/skills/<name>/SKILL.md` directly.

| Skill                    | Trigger                                                                                            |
| ------------------------ | -------------------------------------------------------------------------------------------------- |
| `tdd`                    | Test-driven-development for any implementation                                                     |
| `documenting-decisions`  | Any implementation task — place `DECISION:` markers                                                |
| `requesting-code-review` | After completing implementation                                                                    |
| `caveman`                | Compact wording when writing prose (issues description, PR description, comments on repo or code)  |
| `grill-me`               | User asks to be grilled/interviewed about a plan or design before implementation                   |
| `grill-with-docs`        | Grilling session that also records ADRs and glossary entries as decisions are made                 |
| `grilling`               | Core interview loop used by `grill-me`/`grill-with-docs`; also on any 'grill' trigger phrase       |
| `domain-modeling`        | Pinning down domain terminology (glossary in `docs/glossary/`) or recording decisions in design    |
| `writing-adrs`           | Recording an architectural decision as an ADR in `docs/adr/`, or when another skill flags one      |
| `to-tickets`             | Splitting approved work into tracer-bullet issues with blocking edges (reproducible-spec rules)    |
| `to-spec`                | Turning the current conversation into a spec/PRD and publishing it to the tracker                  |

### Repo-Local Skill Overrides

- `grilling`: present each question via the platform's multiple-choice dialog (e.g. `AskUserQuestion` in Claude Code) when the platform supports one; fall back to plain-text questions otherwise.

## Git

- Branch: `<agent>/<issue-number>-<desc>` (e.g. `hermes/42-fix-auth`, `claude/42-fix-auth`)
- Never push to `main`
- Create PR immediately on branch creation
- Commits: conventional commits
- Document unexpected encounters and design decisions in commit message as well as PR/Issue

### Agentic Engineering Workflow

Use `ghx` for all repository interaction. `gh` and `tea` are disabled — calling them tells you to use `ghx` instead (enforced via shims in `scripts/agent-shims/`, on PATH in agent sessions only; tracker access through MCP tools is not gated by the shims).

#### Available `ghx` verbs

- **issues:** `issue create`, `issue view` (`--comments`), `issue list`, `issue comment`, `issue edit`
- **pull requests:** `pr create`, `pr view` (`--comments`), `pr list`, `pr comment`, `pr edit`, `pr review` (`--body`, repeatable `--code-comment path:line:text`), `pr checks`, `pr status`
- **CI:** `run list`, `run view`

`ghx` exposes a curated subset of `gh`'s verbs (plus a few additions, e.g. `--code-comment`) and presents the **same `gh`-style interface against both GitHub and Forgejo**, so you never need to know which host the repo is on. It is **not** a full `gh` replacement: it has only the verbs listed above. If a command isn't in that list, `ghx` doesn't have it — don't fall back to `gh`/`tea`.

Use `run list` / `run view` for workflow-run detail; use `pr checks` / `pr status` for a PR's check rollup.

The modes below are the kinds of work the user will ask for. **Each runs in its own session — possibly a different model or agent** (Review especially). Follow the named skills at each step.

#### Plan

- Explore the codebase. Flag `DECISION:SCOPE` when resolving ambiguities. Use the `documenting-decisions` skill (refs: `pre-approval-gate.md`, `scope-interpretation.md`).
- Write an issue → `ghx issue create`
- Set issue metadata → `ghx issue edit` (labels/assignees/milestone)

#### Implement

- Read the given issue and comments → `ghx issue view --comments`
- Do Test-Driven Development per the `tdd` skill.
- Implement the minimal code to pass tests, then the remaining code per the ticket spec. Place `DECISION:` markers per the `documenting-decisions` skill (refs: `decision-markers.md`, `marker-examples.md`).
- Commit discipline:
  - One test → one commit → one implementation for that test → one commit
  - `prek` must pass on every commit (lint/format hooks only — prek never runs unit tests).
  - TDD red-step commits are expected and required (a commit whose new tests fail but whose lint/format passes). **CI evaluates at PR HEAD, not per-commit**, so a red-step commit does not constitute a CI failure — do not treat it as one.
  - Don't fix lint manually — run the formatter. Only touch code directly if the tools can't resolve it.
- Push → `git push` *(plain git; git is not routed through `ghx`)*
- Create the PR if not already present, and link it to the issue both ways → `ghx pr create` (start with `Closes #<number>` in description), then `ghx issue edit` if a back-reference is needed. **If a PR already exists for this branch, do not create or re-link it** — skip to CI.
  PR body must include:
  - `Closes #<number>`.
  - Any obstacles that diverged from the initial plan, and — in the rare event spec deviation was unavoidable — what deviated and why.
  - All `DECISION:` markers present in the diff, rendered per the `documenting-decisions` skill format.
- Check CI → `ghx run list` / `ghx run view` (or `ghx pr checks` once the PR exists).
- If CI fails, fix it by re-entering this **Implement** workflow.

#### Review

- Read the given issue and comments → `ghx issue view --comments`
- Review the PR and give Critical / Important feedback per the `requesting-code-review` skill.
- Submit it as a single review → `ghx pr review`:
  - PR-level summary feedback → `--body "..."`
  - Feedback tied to specific lines → repeatable `--code-comment path:line:text`
  - Put both in the same `ghx pr review` call; don't split a review across `pr review` and `pr comment`.

#### Apply Review Comments

- Read the given issue and comments → `ghx issue view --comments`
- Read PR comments and code comments → `ghx pr view --comments`
- If the review uncovers inconsistencies in the issue, **comment** on it freely → `ghx issue comment`
- Only **edit** issue content when the user explicitly requests it → `ghx issue edit`. Editing is gated on explicit request because it can overwrite human-authored intent; commenting is always safe, editing is not.
- Then re-enter the **Implement** workflow.

## Commands

`make <cmd>`: `check`, `test`, `unit-test`, `lint`, `mypy`, `auto-format`, `install`, `main`, `run`, `help`

## Dependencies

Add packages using the package manager only — `uv add <package>` in this repo — never edit requirements/dependencies directly (since your knowledge cut-off prevents you from knowing the latest version of the packages).

## Documentation

- All non-trivial functions must have contracts in the function doc string
- Document all params, return shapes, and every possible error response
- Test cases must cover edge cases for inputs and every @returns line in the contract
- Non-trivial decisions or behavior should be documented via inline comments
