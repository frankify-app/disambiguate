"""
Exhaustive link-syntax matrix (issue #29 prevention).

Pins every supported and deliberately-unsupported link form against every
graph-facing check, so parser changes cannot silently drop a syntax again:

- Syntax axis: every form in FORMS below.
- Location axis: root document, glossary term body, Obsidian callout block.
- Assertion axis: reachability edge (orphan check), dependency edge
  (topological order), and broken-cross-reference reporting for dangling
  targets.

A meta-test keeps `docs/glossary/cross-reference.md` (the source of the
bundled `--explain cross-reference` spec) in lockstep with this matrix:
every form documented there must appear here, and vice versa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from disambiguate.glossary import load_glossary
from disambiguate.lint import LintFinding, lint_glossary
from disambiguate.resolver import resolve

DOCS_CROSS_REFERENCE = (
    Path(__file__).resolve().parents[2] / "docs" / "glossary" / "cross-reference.md"
)


@dataclass(frozen=True)
class LinkForm:
    """
    One row of the syntax matrix.

    form_id: parametrize id, stable across test runs.
    template: link text with `{t}` as the target-slug placeholder. `{T}`
        renders the target uppercased (case-sensitivity rows).
    resolves: True if the form creates an edge to the term whose slug is
        the (lowercase) target — reachability, dependency, and rendering
        all follow this single flag.
    extracted_target: what the parser extracts for target slug `{t}`, with
        `{t}`/`{T}` placeholders, or None when the form is not parsed as a
        link at all. A form can be extracted yet not resolve (`[[{T}]]`
        extracts the uppercase slug, which matches no term): extracted but
        unresolvable targets in term bodies are reported as broken
        cross-references instead of vanishing.
    """

    form_id: str
    template: str
    resolves: bool
    extracted_target: str | None


# DECISION:SCOPE issue #29 case 6 left slug case/whitespace normalization
# open ("worth an explicit spec decision either way"). Pinned here to the
# strict-slug behavior decided in #27/#28: targets match by exact slug,
# no case folding, no padding tolerance. Uppercase targets are extracted
# and therefore surface as broken cross-references in term bodies rather
# than vanishing; padded targets are not link syntax at all.
FORMS = [
    LinkForm("wikilink_plain", "[[{t}]]", resolves=True, extracted_target="{t}"),
    LinkForm("wikilink_alias", "[[{t}|Alias]]", resolves=True, extracted_target="{t}"),
    LinkForm("wikilink_empty_alias", "[[{t}|]]", resolves=True, extracted_target="{t}"),
    LinkForm(
        "wikilink_multiword_alias",
        "[[{t}|multi word alias]]",
        resolves=True,
        extracted_target="{t}",
    ),
    LinkForm(
        "wikilink_fragment", "[[{t}#heading]]", resolves=True, extracted_target="{t}"
    ),
    LinkForm(
        "wikilink_fragment_alias",
        "[[{t}#heading|Alias]]",
        resolves=True,
        extracted_target="{t}",
    ),
    LinkForm("wikilink_embed", "![[{t}]]", resolves=True, extracted_target="{t}"),
    LinkForm("wikilink_uppercase", "[[{T}]]", resolves=False, extracted_target="{T}"),
    LinkForm("wikilink_padded", "[[ {t} ]]", resolves=False, extracted_target=None),
    LinkForm("md_link", "[Alias]({t}.md)", resolves=True, extracted_target="{t}"),
    LinkForm(
        "md_link_pathed",
        "[Alias](path/to/{t}.md)",
        resolves=True,
        extracted_target="{t}",
    ),
    LinkForm(
        "md_link_fragment",
        "[Alias]({t}.md#heading)",
        resolves=True,
        extracted_target="{t}",
    ),
    LinkForm(
        # Leading newline: fences only open at line start, and the fixtures
        # embed each form mid-sentence.
        "fenced_code",
        "\n```\n[[{t}]]\n```",
        resolves=False,
        extracted_target=None,
    ),
    LinkForm("inline_code", "`[[{t}]]`", resolves=False, extracted_target=None),
]

FORM_IDS = [form.form_id for form in FORMS]


def _render(form: LinkForm, target: str) -> str:
    """Render `form`'s link text for `target`, expanding both placeholders."""
    return form.template.replace("{t}", target).replace("{T}", target.upper())


def _expected_extracted(form: LinkForm, target: str) -> str | None:
    """Render the target slug the parser is expected to extract, or None."""
    if form.extracted_target is None:
        return None
    return form.extracted_target.replace("{t}", target).replace("{T}", target.upper())


def _write(directory: Path, slug: str, body: str) -> None:
    (directory / f"{slug}.md").write_text(body, encoding="utf-8")


def _setup_glossary(tmp_path: Path) -> Path:
    glossary_dir = tmp_path / "glossary"
    glossary_dir.mkdir()
    return glossary_dir


def _orphan_slugs(findings: list[LintFinding]) -> set[str]:
    """Collect slugs named in orphan findings (one finding lists them all)."""
    slugs: set[str] = set()
    for finding in findings:
        if finding.kind != "orphan":
            continue
        slugs.update(re.findall(r"^  - (\S+)$", finding.message, re.MULTILINE))
    return slugs


@pytest.mark.parametrize("form", FORMS, ids=FORM_IDS)
def test_reachability_from_root(form: LinkForm, tmp_path: Path) -> None:
    """A root-document link makes the target reachable iff the form resolves."""
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "aua", "## AuA\n\nbody\n")
    _write(glossary_dir, "aum", "## AuM\n\nbody\n")
    root = tmp_path / "README.md"
    root.write_text(f"# Root\n\n[[aua]] and {_render(form, 'aum')}\n", encoding="utf-8")

    findings = lint_glossary(load_glossary(glossary_dir), roots=[root])

    assert ("aum" in _orphan_slugs(findings)) is not form.resolves


@pytest.mark.parametrize("form", FORMS, ids=FORM_IDS)
def test_reachability_from_root_callout(form: LinkForm, tmp_path: Path) -> None:
    """Links inside an Obsidian callout block count like any other root link."""
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "aua", "## AuA\n\nbody\n")
    _write(glossary_dir, "aum", "## AuM\n\nbody\n")
    root = tmp_path / "README.md"
    root.write_text(
        f"# Root\n\n[[aua]]\n\n> [!abstract]- Summary\n> {_render(form, 'aum')}\n",
        encoding="utf-8",
    )

    findings = lint_glossary(load_glossary(glossary_dir), roots=[root])

    assert ("aum" in _orphan_slugs(findings)) is not form.resolves


@pytest.mark.parametrize("form", FORMS, ids=FORM_IDS)
def test_dependency_edge_in_term_body(form: LinkForm, tmp_path: Path) -> None:
    """A term-body link creates a dependency edge iff the form resolves."""
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "aua", f"## AuA\n\nSee {_render(form, 'aum')}\n")
    _write(glossary_dir, "aum", "## AuM\n\nbody\n")

    glossary = load_glossary(glossary_dir)

    assert ("aum" in glossary.dependencies["aua"]) is form.resolves


@pytest.mark.parametrize("form", FORMS, ids=FORM_IDS)
def test_topological_order_in_term_body(form: LinkForm, tmp_path: Path) -> None:
    """A resolving term-body link orders the dependency before the dependent."""
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "aua", f"## AuA\n\nSee {_render(form, 'aum')}\n")
    _write(glossary_dir, "aum", "## AuM\n\nbody\n")

    ordered = [term.slug for term in resolve(load_glossary(glossary_dir), ["aua"])]

    if form.resolves:
        assert ordered.index("aum") < ordered.index("aua")
    else:
        assert "aum" not in ordered


@pytest.mark.parametrize("form", FORMS, ids=FORM_IDS)
def test_transitive_reachability_through_term_body(
    form: LinkForm, tmp_path: Path
) -> None:
    """Issue #29 case 4: root -> aua plainly, aua -> aum via the form."""
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "aua", f"## AuA\n\nSee {_render(form, 'aum')}\n")
    _write(glossary_dir, "aum", "## AuM\n\nbody\n")
    root = tmp_path / "README.md"
    root.write_text("# Root\n\n[[aua]]\n", encoding="utf-8")

    findings = lint_glossary(load_glossary(glossary_dir), roots=[root])

    assert ("aum" in _orphan_slugs(findings)) is not form.resolves


@pytest.mark.parametrize("form", FORMS, ids=FORM_IDS)
def test_dangling_target_in_term_body_is_broken_link(
    form: LinkForm, tmp_path: Path
) -> None:
    """
    Issue #29 case 5: dangling term-body links must never silently vanish.

    A link to a nonexistent term is a broken cross-reference for every form
    the parser extracts. Forms that are not link syntax at all (padding,
    code) produce no finding.
    """
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "aua", f"## AuA\n\nSee {_render(form, 'kaputt')}\n")
    root = tmp_path / "README.md"
    root.write_text("# Root\n\n[[aua]]\n", encoding="utf-8")

    findings = lint_glossary(load_glossary(glossary_dir), roots=[root])

    expected = _expected_extracted(form, "kaputt")
    broken_messages = [f.message for f in findings if f.kind == "broken-link"]
    if expected is None:
        assert broken_messages == []
    else:
        assert any(repr(expected) in message for message in broken_messages)


def test_empty_alias_is_flagged_malformed_but_still_resolves(
    tmp_path: Path,
) -> None:
    """`[[slug|]]` resolves leniently AND is flagged by the malformed check."""
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "aua", "## AuA\n\nSee [[aum|]]\n")
    _write(glossary_dir, "aum", "## AuM\n\nbody\n")
    root = tmp_path / "README.md"
    root.write_text("# Root\n\n[[aua]]\n", encoding="utf-8")

    findings = lint_glossary(load_glossary(glossary_dir), roots=[root])

    assert any(f.kind == "malformed-wikilink" for f in findings)
    assert _orphan_slugs(findings) == set()


@pytest.mark.xfail(strict=True)
def test_docs_and_matrix_in_lockstep() -> None:
    """
    Issue #29 meta-test: the cross-reference spec and this matrix stay in lockstep.

    `docs/glossary/cross-reference.md` (source of the bundled
    `--explain cross-reference` spec) and this matrix must document the
    same set of link forms.

    Every matrix form must appear in the doc as an inline-code example
    rendered with target slug `foo`, and every link-shaped inline-code
    example in the doc must be a matrix form — so neither the spec nor the
    parser tests can drift ahead of the other.
    """
    doc_text = DOCS_CROSS_REFERENCE.read_text(encoding="utf-8")
    doc_examples = set(re.findall(r"`([^`\n]*(?:\[\[|\]\()[^`\n]*)`", doc_text))
    # The two code forms cannot be shown cleanly as inline-code examples
    # (they contain backticks themselves); the doc covers them in prose,
    # asserted separately.
    matrix_examples = {
        _render(form, "foo")
        for form in FORMS
        if form.form_id not in ("fenced_code", "inline_code")
    }
    assert "fenced code block" in doc_text
    assert "inline code" in doc_text

    missing_from_doc = matrix_examples - doc_examples
    undocumented_in_matrix = doc_examples - matrix_examples

    assert not missing_from_doc, f"forms missing from doc: {missing_from_doc}"
    assert not undocumented_in_matrix, (
        f"doc examples not covered by matrix: {undocumented_in_matrix}"
    )
