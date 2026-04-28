## Glossary

A directory of [term](term.md) files. The glossary is the unit Disambiguate
operates on: load it, resolve from it, render from it, lint it.

By convention the glossary lives at `docs/glossary/` or `glossary/` at the
root of a project. Disambiguate auto-discovers the nearest such directory by
walking up from the current working directory. The location can be overridden
with `--glossary <path>` or the `DISAMBIGUATE_GLOSSARY` environment variable.

A glossary contains zero or more terms. Slug uniqueness is enforced across
the directory — two files with the same basename are an error.
