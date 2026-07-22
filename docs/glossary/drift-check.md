## Drift-check

One named, coded rule detecting a class of [drift](drift.md). Every
drift-check has a stable [rule-code](rule-code.md), reports offending
[term-mentions](term-mention.md) as fatal findings, and exits the `--drift`
run non-zero when any finding survives.

Shipped drift-checks:

- `unlinked-term`: a document mentions a [term](term.md) in plain prose but
  never links it. Linking the term once anywhere in the document satisfies
  the rule for every mention in that document — first-occurrence linking is
  the convention, later plain mentions are fine. A term used with a
  non-glossary (colloquial) meaning is intentionally the same finding: an
  unlinked mention either should be linked or should be reworded.
- `wrong-alias`: prose uses an [avoided-term](avoided-term.md) — a
  forbidden synonym — where the canonical term is meant. The finding names
  the canonical term to use instead.
