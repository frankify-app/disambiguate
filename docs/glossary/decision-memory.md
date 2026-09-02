## Decision-memory

<!-- d10e: auto-prune -->
<!-- Copier-vendored from the agentic-engineering-template — do NOT edit
     here; change it in the template and pull via `copier update`. The
     auto-prune marker above lets `disambiguate prune` remove this term
     from a repo that never links it. -->

The private, data-only store of [decision records](decision-record.md) and
the [preference set](preference-set.md). It is the terminal store:
records stay individual immutable files (no compaction),
because per-record review and append-only history are the point. Reached at
runtime via `DECISION_MEMORY_URL`, never a committed URL.
