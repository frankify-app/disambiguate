## Obsidian format

The [glossary-format](glossary-format.md) variant intended for use as an
Obsidian vault. Terms live in a folder inside the vault, browsed and edited
through Obsidian.

[Cross-references](cross-reference.md) typically use the wiki-style syntax:
`[[slug]]`. Obsidian renders these as live, clickable backlinks and shows
them in the graph view, which is the main reason to choose this variant.

Display text is supported: `[[slug|display text]]` resolves to `slug`; the
text after the pipe is presentation-only and the link renders verbatim.
Heading and block targets (`[[slug#heading]]`, `[[slug#^block]]`) also
resolve to `slug` — the fragment is ignored. Malformed pipe forms
(`[[|text]]`, `[[slug|]]`, `[[a|b|c]]`) fail [lint](lint.md) in glossary
files, though rendering stays lenient and resolves the first segment.

Standard markdown links (`[label](other.md)`) also work for the resolver
and render correctly in Obsidian, but lose the backlink and graph view
benefits. Use wiki-style links by preference; fall back to markdown links
only when a particular section needs custom link text.

The on-disk file shape is identical to the GitHub format variant — the
same glossary directory can serve both audiences if links are written in
either syntax consistently.
