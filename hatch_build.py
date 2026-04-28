"""
Hatchling build hook.

Copies the bundled glossary from `docs/glossary/` into staged package data as
`disambiguate/_glossary/`, and writes `disambiguate/_terms.py` containing the
alphabetical list of slugs. The source of truth is `docs/glossary/`.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class GlossaryBuildHook(BuildHookInterface):  # type: ignore[type-arg]
    """Generate `_glossary/` and `_terms.py` from `docs/glossary/`."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        root = Path(self.root)
        source_glossary = root / "docs" / "glossary"
        target_package = (
            Path(self.directory) / "generated" / self.target_name / "disambiguate"
        )
        target_glossary = target_package / "_glossary"
        terms_file = target_package / "_terms.py"

        if not source_glossary.is_dir():
            raise FileNotFoundError(
                f"Bundled glossary source missing: {source_glossary}"
            )

        if self.target_name == "sdist":
            return

        if target_glossary.exists():
            shutil.rmtree(target_glossary)
        target_glossary.mkdir(parents=True)

        slugs: list[str] = []
        for md in sorted(source_glossary.glob("*.md")):
            shutil.copy2(md, target_glossary / md.name)
            slugs.append(md.stem)

        slugs.sort()
        terms_literal = ",\n".join(f"    {slug!r}" for slug in slugs)
        terms_file.write_text(
            '"""Auto-generated. Do not edit. Populated by hatch_build.py."""\n\n'
            f"TERMS: tuple[str, ...] = (\n{terms_literal},\n)\n",
            encoding="utf-8",
        )
        # DECISION:ARCH — Stage generated package data under Hatch's build
        # directory so package builds do not mutate the source tree.
        force_include = build_data.setdefault("force_include", {})
        force_include[str(target_glossary)] = self._archive_path("_glossary")
        force_include[str(terms_file)] = self._archive_path("_terms.py")

    def _archive_path(self, package_path: str) -> str:
        """Return the artifact path for the active Hatch target."""
        return f"disambiguate/{package_path}"
