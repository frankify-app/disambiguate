## Avoided-term

A forbidden synonym for a canonical [term](term.md), declared on the term
file's `_Avoid_:` line — a single line of comma-separated aliases:

```markdown
_Avoid_: gadget, doohickey
```

Using an avoided-term in prose where the canonical term is meant is
[drift](drift.md): the `wrong-alias` drift detection rule reports it and
names the canonical term to use instead. The `_Avoid_:` line is the single
source of truth — it is rendered to readers and parsed by the checker
alike (ADR 0001).

Aliases match exactly, on word boundaries. No inflection is inferred, so a
plural is a separate alias: declaring `backlink` does not catch
`backlinks`. Declare each form the prose might use. Aliases may be several
words (`dependency order`), and matching skips code spans, fences, and
existing links like every other check for drifts.

An `_Avoid_:` line inside a code fence or span is an example, not a
declaration — a document may show the grammar without adopting it.
