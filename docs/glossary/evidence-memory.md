## Evidence-memory

<!-- d10e: auto-prune -->
<!-- Copier-vendored from the agentic-engineering-template — do NOT edit
     here; change it in the template and pull via `copier update`. The
     auto-prune marker above lets `disambiguate prune` remove this term
     from a repo that never links it. -->

The private, data-only store of detection records: bugs and features
found while working, one immutable file per detection — the substrate
for dedup, lookup, and later regression tests. Reached at runtime via
`EVIDENCE_MEMORY_URL`, never a committed URL.
