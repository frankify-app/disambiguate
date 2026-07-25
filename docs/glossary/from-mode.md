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
- A `.md` link whose basename matches no term is resolved against the
  source document when `--from` was given a real path: if the link's path
  points at an existing file, it is a document link and is ignored — the
  same classification the [lint](lint.md) reachability walk applies. If it
  points at nothing, it is an error. From-mode does not silently ignore
  unresolvable references.
- On standard input there is no base path to resolve against, so every
  `.md` link whose basename matches no term is an error. Unknown wikilinks
  are always an error — they address terms by slug and carry no path.
- Non-glossary links (external URLs, image paths, links to non-`.md` files)
  are silently ignored.

Output is identical to a direct `disambiguate <slug> ...` invocation: the
dependency closure in topological order.
