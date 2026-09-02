## Record contract

<!-- d10e: auto-prune -->
<!-- Copier-vendored from the agentic-engineering-template — do NOT edit
     here; change it in the template and pull via `copier update`. The
     auto-prune marker above lets `disambiguate prune` remove this term
     from a repo that never links it. -->

The universal shape shared by all record stores: one immutable JSON file per
record, ID = timestamp + slug, minted schema version `v`, unknown fields
tolerated. One writer core and one validator core serve every store; only
lifecycle policy differs per store.
