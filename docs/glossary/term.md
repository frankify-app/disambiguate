## Term

A unit of vocabulary in a glossary. Each term is a single markdown file: one
file, one definition.

The file's basename (with `.md` stripped) is the term's stable identifier, and
the file's first H2 heading is the term's canonical name. The body is free-form
markdown — usually a short definition, sometimes with examples or links to
related terms.

A term is the atomic unit Disambiguate operates on. Resolving, rendering,
linting, and dependency tracking all happen at the term level.
