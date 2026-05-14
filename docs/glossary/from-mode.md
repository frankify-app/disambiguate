## From-mode

The CLI mode triggered by `--from <path>`: extract glossary-shaped
[cross-references](cross-reference.md) from a document, then run the
[resolver](resolver.md) over the extracted [slugs](slug.md).

The path argument can be `-` (or omitted entirely) to read the source
document from standard input. Useful for piping prose through Disambiguate
to produce a glossary preamble for whatever vocabulary it actually uses.

Link classification:

- A link whose basename matches a slug in the active glossary is treated as
  a request for that term.
- A glossary-shaped link with a broken slug — basename ending in `.md` but
  not matching any term — is an error. From-mode does not silently ignore
  unresolvable references.
- Non-glossary links (external URLs, image paths, links to non-`.md` files)
  are silently ignored.

Output is identical to a direct `disambiguate <slug> ...` invocation: the
dependency closure in topological order.
