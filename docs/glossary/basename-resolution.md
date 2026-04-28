## Basename resolution

The rule that a [cross-reference](cross-reference.md) is resolved to a term
purely by its basename, ignoring any directory components and the `.md`
extension.

All three of the following resolve identically to the term with
[slug](slug.md) `foo`:

- `[label](foo.md)`
- `[label](path/to/foo.md)`
- `[[foo]]`

This means a glossary can be moved or reorganized without rewriting links,
and the same term can be referenced consistently regardless of where the
referencing file lives. The trade-off: two terms cannot share a basename
even if they live in different subdirectories.

Non-`.md` links and absolute URLs are not subject to basename resolution and
are ignored entirely by the resolver.
