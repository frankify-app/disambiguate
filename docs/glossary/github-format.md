## GitHub format

The [glossary-format](glossary-format.md) variant intended for GitHub
projects. Terms live at `docs/glossary/` (or another path inside the repo)
and are rendered by GitHub's standard markdown renderer.

[Cross-references](cross-reference.md) use standard markdown links:
`[label](other.md)` or `[label](path/to/other.md)`. GitHub renders these
inline; the link target resolves at the repository level when viewed on
GitHub.

Wiki-style `[[slug]]` links also work for Disambiguate's purposes — they
will not render as live links on GitHub, but the resolver still picks them
up. Use them only if you also intend the glossary to be browsable as an
Obsidian vault.

This is the default variant. A new project setting up a glossary should
assume the GitHub format unless there is a specific reason to do otherwise.
