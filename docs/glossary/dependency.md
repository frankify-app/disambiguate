## Dependency

A directed edge from one [term](term.md) to another, created by a
[cross-reference](cross-reference.md) inside the term's body. If term `a`
cross-references term `b`, then `a` depends on `b`: `b` must appear before
`a` in the rendered output, because `a`'s definition assumes `b` is already
defined.

Dependencies are transitive. Resolving a term pulls in everything it depends
on, recursively. The complete dependency closure of a term is the set of all
terms reachable by following edges out from it.

The dependency graph is required to be acyclic. Cycles are a lint error —
they make ordering impossible.
