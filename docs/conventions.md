# Disambiguate — Project Conventions

Repo-specific rules referenced from [AGENTS.md](../AGENTS.md). This file is
seeded once by the agentic template and never overwritten by `copier update` —
edit it freely.

## Commands

`make <cmd>`: `check`, `test`, `unit-test`, `lint`, `mypy`, `auto-format`,
`install`, `main`, `run`, `help`.

## Dependencies

Add packages with `uv add <package>` only — never edit
requirements/dependencies directly.
