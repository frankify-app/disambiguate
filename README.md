# Disambiguate

<p align="center">
  <a href="https://github.com/frankify-app/disambiguate/actions/workflows/ci.yml?query=branch%3Amain">
    <img src="https://img.shields.io/github/actions/workflow/status/frankify-app/disambiguate/ci.yml?branch=main&label=CI&logo=github&style=flat-square" alt="CI Status" >
  </a>
  <a href="https://codecov.io/gh/frankify-app/disambiguate">
    <img src="https://img.shields.io/codecov/c/github/frankify-app/disambiguate.svg?logo=codecov&logoColor=fff&style=flat-square" alt="Test coverage percentage">
  </a>
</p>
<p align="center">
  <a href="https://github.com/astral-sh/uv">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv">
  </a>
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff">
  </a>
  <a href="https://github.com/j178/prek">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/j178/prek/master/docs/assets/badge-v0.json" alt="prek">
  </a>
</p>
<p align="center">
  <a href="https://pypi.org/project/disambiguate/">
    <img src="https://img.shields.io/pypi/v/disambiguate.svg?logo=python&logoColor=fff&style=flat-square" alt="PyPI Version">
  </a>
  <img src="https://img.shields.io/pypi/pyversions/disambiguate.svg?style=flat-square&logo=python&amp;logoColor=fff" alt="Supported Python versions">
  <img src="https://img.shields.io/pypi/l/disambiguate.svg?style=flat-square" alt="License">
</p>

---

**Source Code**: <a href="https://github.com/frankify-app/disambiguate" target="_blank">https://github.com/frankify-app/disambiguate </a>

---

Disambiguate resolves markdown glossary terms and their transitive
dependencies in topological order. Point it at a directory of `*.md` term
files in either [GitHub format](https://github.com/frankify-app/disambiguate/blob/main/docs/glossary/github-format.md)
or [Obsidian format](https://github.com/frankify-app/disambiguate/blob/main/docs/glossary/obsidian-format.md),
ask for a slug or two, and get back a self-contained markdown document
where every term is defined before it is referenced.

## Quickstart

```bash
uvx disambiguate                       # render the entire glossary
uvx disambiguate topological-order     # render one term and its dependency closure
uvx disambiguate --from notes.md       # extract glossary-shaped links from a doc
uvx disambiguate --explain             # render Disambiguate's own bundled spec
uvx disambiguate --lint                # validate the glossary
```

The runtime is stdlib-only — `pip install disambiguate` brings in nothing
else. `uvx` works without an explicit install.

## Installation

```bash
pip install disambiguate
```

## How it works

The pipeline parses each [term](https://github.com/frankify-app/disambiguate/blob/main/docs/glossary/term.md)
into a body plus a list of [cross-references](https://github.com/frankify-app/disambiguate/blob/main/docs/glossary/cross-reference.md),
builds a [dependency](https://github.com/frankify-app/disambiguate/blob/main/docs/glossary/dependency.md)
graph from those references, then runs the
[resolver](https://github.com/frankify-app/disambiguate/blob/main/docs/glossary/resolver.md)
to produce [topological order](https://github.com/frankify-app/disambiguate/blob/main/docs/glossary/topological-order.md).
The same pipeline backs
[from-mode](https://github.com/frankify-app/disambiguate/blob/main/docs/glossary/from-mode.md)
and `--explain`.

For the architectural map, see
[docs/architecture.md](https://github.com/frankify-app/disambiguate/blob/main/docs/architecture.md).
For the full vocabulary, see the
[bundled glossary](https://github.com/frankify-app/disambiguate/blob/main/docs/glossary/disambiguate.md)
— Disambiguate's own dogfood.

## Contributing

See [CONTRIBUTING.md](https://github.com/frankify-app/disambiguate/blob/main/CONTRIBUTING.md).
Conventional commits required — the release workflow uses them to compute
the next version.
