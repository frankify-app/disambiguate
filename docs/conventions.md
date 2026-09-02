# Disambiguate — Project Conventions

Repo-specific rules referenced from [AGENTS.md](../AGENTS.md). This file is
seeded once by the agentic template and never overwritten by `copier update` —
edit it freely.

## Introducing new terms

Follow the link-as-if-exists convention (see
[glossary/cross-reference.md](glossary/cross-reference.md)): a new
domain concept is introduced by cross-referencing its slug *as if the term
file already existed*, then creating `docs/glossary/<slug>.md`. Until the
file exists, `--lint` reports the link as a fatal broken cross-reference —
that is the enforcement, not a bug.

Tickets declare new vocabulary under an `Introduces:` list, one slug per
line, each linked as if it existed:

```markdown
## Introduces

- [drift-baseline](../blob/main/docs/glossary/drift-baseline.md) — checked-in record of grandfathered drift
```

The `Introduces:` list is the durable record of the vocabulary a ticket
intends to add; the linked term files are created by the ticket's
implementation.

## Commands

`make <cmd>`: `check`, `test`, `unit-test`, `lint`, `mypy`, `auto-format`,
`install`, `main`, `run`, `help`.

## Dependencies

Add packages with `uv add <package>` only — never edit
requirements/dependencies directly.
