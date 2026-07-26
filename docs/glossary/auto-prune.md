## Auto-prune

`auto-prune` is an annotation a [term](term.md) carries
to declare that it may be removed once nothing links it.
It is the consent the pruning command requires before deleting a term.

It is written as an HTML comment on the `d10e` annotation surface,
so it stays invisible in rendered markdown
and leaves the H2-first invariant intact:

```markdown
## Grilling

<!-- d10e: auto-prune -->

The structured interview loop that …
```

The annotation carries no provenance —
no owner, no origin, no notion of who wrote the term or where it came from.
Disambiguate is repo-local
and does not model anything outside the repo it runs in.
A producer of a shared term set stamps the marker;
that the set came from elsewhere is invisible here, and deliberately so.
