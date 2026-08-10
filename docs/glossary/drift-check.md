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
A capitalization check (`term-case`) was specified in T5 (#39) and is not
shipped. Expected casing was derived from the term's H2 heading, but a
single-word heading gives no evidence either way — every H2 capitalizes
its first letter, so a genuine proper noun like `Disambiguate` is
indistinguishable from heading style and derives as a common noun. On this
repo the rule's only findings were that misclassification, so it fired on
nothing true. It needs the per-term override from backlog B2 (#41) to
classify correctly; #39 stays open until then.
