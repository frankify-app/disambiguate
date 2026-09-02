# Claude Code Specific Project Instructions

**First:** Read `AGENTS.md`. Follow all instructions and skills there.

## Environment Tooling

In managed environments (e.g. Claude Code on the Web), ALWAYS use the
tooling the environment itself declares (e.g. GitHub MCP tools for
GitHub operations). Never fall back to `gh`, `ghx`, `curl`, or similar
CLIs there — the environment actively sabotages them. The environment's
tool declarations override any command examples elsewhere in this repo,
including `AGENTS.md`.

## Forge Budget

API budget per-account, shared by all sessions.

- No PR subscriptions unless the principal asks.
- Git before REST. Clone answers: file contents, diffs, history,
  branch state. API only for: check runs, job logs, comments,
  reviews, labels, PR/issue state.
- Fetch only needed fields and items; need everything → few large
  pages. Already-fetched state is cached until an event invalidates
  it.

## Learnings

New non-obvious findings — tools, environment, failure modes — go in
this file, tersely.

## Pull Requests

Share PR URL in response to user.
