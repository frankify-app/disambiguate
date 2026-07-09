# Decision markers

When making a noteworthy decision during implementation, annotate it inline in the code:

    // DECISION:<CATEGORY> — <explanation>

Categories: ARCH, SCOPE, IFACE, SEC, IRREV, NOVEL

Use these when:

- ARCH: introducing a new abstraction, dependency, data model, or component boundary
- SCOPE: resolving an ambiguity in the task by choosing an interpretation
- IFACE: changing a public API, config schema, CLI flag, or env var
- SEC: modifying auth, crypto, network, permissions, or input validation
- IRREV: creating a migration, deletion, deployment change, or external side effect
- NOVEL: writing code with no existing pattern in the repo to follow

Do not mark routine changes. If nothing is noteworthy, no markers are needed.

After completing the task, generate DECISION_LOG.md by collecting all DECISION: markers from changed files:

    # Decision Log — [task one-liner]
    ## Decisions requiring review
    - **CATEGORY** `file:line` — explanation
    ## Routine changes (skip review)
    [One-line summary]

If no markers exist, write: "No noteworthy decisions. All changes follow existing patterns."
