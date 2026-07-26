"""
Tests for disambiguate.prune.

Pruning removes terms nothing links. Consent is declared in the term
itself via the `auto-prune` annotation, so the orphan check keeps full
teeth instead of growing an exemption.
"""

from __future__ import annotations

from pathlib import Path

from disambiguate.glossary import Glossary, load_glossary
from disambiguate.prune import plan_prune

CONSENT = "<!-- d10e: auto-prune -->"


def write_glossary(root: Path, terms: dict[str, str]) -> None:
    """Write `slug -> body` term files into a glossary directory."""
    root.mkdir(parents=True, exist_ok=True)
    for slug, body in terms.items():
        (root / f"{slug}.md").write_text(body, encoding="utf-8")


def build(
    tmp_path: Path, terms: dict[str, str], readme: str = ""
) -> tuple[Glossary, list[Path]]:
    """Return (glossary, roots) for a glossary plus a README root."""
    glossary_dir = tmp_path / "docs" / "glossary"
    write_glossary(glossary_dir, terms)
    readme_path = tmp_path / "README.md"
    readme_path.write_text(readme, encoding="utf-8")
    return load_glossary(glossary_dir), [readme_path]


def test_prune_removes_consenting_orphans_and_spares_linked_ones(
    tmp_path: Path,
) -> None:
    """
    Consent alone is not enough — a linked term is in use.

    The whole point is that a repo converges to exactly the terms it
    links, so consent plus orphanhood is the removal condition.
    """
    glossary, roots = build(
        tmp_path,
        {
            "linked": f"## Linked\n\n{CONSENT}\n\nIn use.\n",
            "unlinked": f"## Unlinked\n\n{CONSENT}\n\nNobody links this.\n",
        },
        readme="See [linked](docs/glossary/linked.md).\n",
    )

    plan = plan_prune(glossary, roots)

    assert plan.remove == ["unlinked"]
    assert plan.additional == []


def test_all_orphans_widens_scope_to_terms_that_never_consented(
    tmp_path: Path,
) -> None:
    """Without the flag, a non-consenting orphan is only reported."""
    glossary, roots = build(
        tmp_path,
        {
            "consenting": f"## Consenting\n\n{CONSENT}\n\nOpted in.\n",
            "silent": "## Silent\n\nNever opted in.\n",
        },
    )

    default = plan_prune(glossary, roots)
    assert default.remove == ["consenting"]
    assert default.additional == ["silent"]

    widened = plan_prune(glossary, roots, all_orphans=True)
    assert widened.remove == ["consenting", "silent"]
    assert widened.additional == []


def test_removing_orphans_cannot_orphan_a_surviving_term(tmp_path: Path) -> None:
    """
    The cascade #52 worried about cannot happen.

    Orphanhood is reachability from the roots, so a reachable term's
    whole path is reachable. `deep` is reachable via `hub`, and neither
    is touched even though `island` — which also links `deep` — goes.
    """
    glossary, roots = build(
        tmp_path,
        {
            "hub": "## Hub\n\nLinks [deep](deep.md).\n",
            "deep": "## Deep\n\nReachable through hub.\n",
            "island": f"## Island\n\n{CONSENT}\n\nAlso links [deep](deep.md).\n",
        },
        readme="See [hub](docs/glossary/hub.md).\n",
    )

    plan = plan_prune(glossary, roots)

    assert plan.remove == ["island"]
