## Topological order

An ordering of terms such that every term appears after all the terms it
[depends](dependency.md) on. When the rendered output is read top to bottom,
nothing is referenced before it has been defined.

Topological order is not unique: when multiple terms are independent of each
other (neither transitively depends on the other), they can appear in any
relative order. Disambiguate produces one valid ordering — stable under
re-runs, but not the only one possible.

Computed using `graphlib.TopologicalSorter` from the Python standard library.
A cycle in the dependency graph makes topological ordering impossible and is
reported as a lint error.
