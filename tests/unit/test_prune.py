"""
Tests for disambiguate.prune.

Pruning removes terms nothing links. Consent is declared in the term
itself via the `auto-prune` annotation, so the orphan check keeps full
teeth instead of growing an exemption.
"""

from __future__ import annotations

from pathlib import Path

import pytest

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


@pytest.mark.xfail(strict=True, reason="red: prune planning does not exist yet")
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
