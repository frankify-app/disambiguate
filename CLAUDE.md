# Claude Code Specific Project Instructions

**First:** Read `AGENTS.md`. Follow all instructions and skills there.

## Environment Tooling

In managed environments (e.g. Claude Code on the Web), ALWAYS use the
tooling the environment itself declares (e.g. GitHub MCP tools for
GitHub operations). Never fall back to `gh`, `ghx`, `curl`, or similar
CLIs there — the environment actively sabotages them. The environment's
tool declarations override any command examples elsewhere in this repo,
including `AGENTS.md`.

## Pull Requests

Share PR URL in response to user. After push, watch CI via native tooling
(e.g. GitHub API/MCP) and confirm green before reporting done.
