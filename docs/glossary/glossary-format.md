## Glossary format

The shared shape of a Disambiguate-compatible [glossary](glossary.md). A
single directory containing one [term](term.md) per markdown file.

Per-file structure:

- File basename (with `.md` stripped) is the [slug](slug.md). Slugs must be
  unique across the directory and use lowercase ASCII letters, digits, and
  hyphens.
- The first H2 heading (`## Canonical Name`) is the term's display name. The
  H2 is mandatory.
- Body is free-form markdown.
- [Cross-references](cross-reference.md) to other terms use either standard
  markdown (`[text](other.md)`) or wiki-style (`[[other]]`). Both resolve by
  basename.

The format is intentionally minimal — anything outside of H2 + cross-link
syntax is just markdown, rendered as-is. This keeps glossaries portable
between platforms with different markdown extensions, while letting each
platform's variant of the format add its own conventions on top.

Two such variants exist today — one for GitHub-rendered repositories and
one for Obsidian vaults. Both are special cases of the format defined here,
with platform-specific tweaks.
