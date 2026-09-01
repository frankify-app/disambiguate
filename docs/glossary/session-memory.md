## Session-memory

<!-- d10e: auto-prune -->
<!-- Copier-vendored from the agentic-engineering-template — do NOT edit
     here; change it in the template and pull via `copier update`. The
     auto-prune marker above lets `disambiguate prune` remove this term
     from a repo that never links it. -->

The private, data-only store of thread events and transcript exports —
what happened, per [session](agent-session.md). The ledger is append-only, and a
thread's state is computed by folding its events in order — it is
never stored as an editable status field, so the log stays the only
authority. Reached at runtime
via `SESSION_MEMORY_URL`, never a committed URL.
