## Cross-reference

A link from one [term](term.md) to another. Cross-references come in two
syntactic forms, both supported:

- Standard markdown: `[some text](path/to/foo.md)` — resolves to the term
  whose slug matches the link's basename, regardless of path.
- Wiki-style: `[[foo]]` — resolves directly to the term with slug `foo`.
  Display text (`[[foo|shown text]]`) and `#fragment` targets are allowed;
  both resolve to `foo`.

Cross-references are the edges of the dependency graph. A term that
cross-references another depends on it: when rendered, the referenced term
must come first.

Cross-references inside fenced code blocks are ignored — code samples that
happen to contain link-shaped text do not create edges.
