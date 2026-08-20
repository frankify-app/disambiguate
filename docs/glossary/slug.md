## Slug

The stable identifier for a [term](term.md). The slug is the term file's
basename with the `.md` extension stripped: `topological-order.md` has slug
`topological-order`.

Slugs are how terms are addressed everywhere — in CLI arguments, in
cross-references, and in the dependency graph. Direct CLI arguments may also
use a phrase such as `topological order`; Disambiguate normalizes that phrase
to the conventional slug `topological-order` before lookup. Characters outside
`a-z`, `0-9`, and `-` normalize to `-`, and consecutive dashes collapse to a
single dash. The canonical name (the H2 heading inside the file) is for human
reading; the slug is for machine identity.

Slugs must be unique within a glossary. The canonical format is
`^[a-z0-9]+(?:-[a-z0-9]+)*$`: lowercase ASCII letters, digits, and single
hyphens between segments — no leading or trailing hyphen, no consecutive
hyphens. Disambiguate's lint enforces this format.

_Avoid_: term id, term-id, term name
