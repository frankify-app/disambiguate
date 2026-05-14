"""Tests for the Hatch build hook."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _load_hatch_build() -> Any:
    """Load hatch_build.py with a minimal fake Hatchling interface."""
    interface = types.ModuleType("hatchling.builders.hooks.plugin.interface")

    class BuildHookInterface:
        _root: str
        _directory: str
        _target_name: str

        @property
        def root(self) -> str:
            return self._root

        @property
        def directory(self) -> str:
            return self._directory

        @property
        def target_name(self) -> str:
            return self._target_name

    interface.__dict__["BuildHookInterface"] = BuildHookInterface
    sys.modules["hatchling"] = types.ModuleType("hatchling")
    sys.modules["hatchling.builders"] = types.ModuleType("hatchling.builders")
    sys.modules["hatchling.builders.hooks"] = types.ModuleType(
        "hatchling.builders.hooks"
    )
    sys.modules["hatchling.builders.hooks.plugin"] = types.ModuleType(
        "hatchling.builders.hooks.plugin"
    )
    sys.modules["hatchling.builders.hooks.plugin.interface"] = interface

    spec = importlib.util.spec_from_file_location(
        "hatch_build", ROOT / "hatch_build.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_hook_stages_generated_files_outside_source_tree(
    tmp_path: Path,
) -> None:
    """Generated package files are included from the build directory."""
    project = tmp_path / "project"
    source_glossary = project / "docs" / "glossary"
    source_glossary.mkdir(parents=True)
    (source_glossary / "term.md").write_text("## Term\n\nbody\n", encoding="utf-8")
    (project / "src" / "disambiguate").mkdir(parents=True)

    module = _load_hatch_build()
    hook = module.GlossaryBuildHook.__new__(module.GlossaryBuildHook)
    hook._root = str(project)
    hook._directory = str(tmp_path / "build")
    hook._target_name = "wheel"
    build_data: dict[str, Any] = {"force_include": {}}

    hook.initialize("0.0.0", build_data)

    generated_root = tmp_path / "build" / "generated" / "wheel" / "disambiguate"
    assert (generated_root / "_glossary" / "term.md").read_text(
        encoding="utf-8"
    ) == "## Term\n\nbody\n"
    assert (generated_root / "_terms.py").is_file()
    assert not (project / "src" / "disambiguate" / "_glossary").exists()
    assert not (project / "src" / "disambiguate" / "_terms.py").exists()
    assert build_data["force_include"] == {
        str(generated_root / "_glossary"): "disambiguate/_glossary",
        str(generated_root / "_terms.py"): "disambiguate/_terms.py",
    }


def test_build_hook_does_not_stage_generated_files_for_sdist(
    tmp_path: Path,
) -> None:
    """The sdist carries source docs; wheel builds generate package data."""
    project = tmp_path / "project"
    source_glossary = project / "docs" / "glossary"
    source_glossary.mkdir(parents=True)
    (source_glossary / "term.md").write_text("## Term\n\nbody\n", encoding="utf-8")
    (project / "src" / "disambiguate").mkdir(parents=True)

    module = _load_hatch_build()
    hook = module.GlossaryBuildHook.__new__(module.GlossaryBuildHook)
    hook._root = str(project)
    hook._directory = str(tmp_path / "build")
    hook._target_name = "sdist"
    build_data: dict[str, Any] = {"force_include": {}}

    hook.initialize("0.0.0", build_data)

    assert build_data["force_include"] == {}
    assert not (tmp_path / "build" / "generated").exists()
    assert not (project / "src" / "disambiguate" / "_glossary").exists()
    assert not (project / "src" / "disambiguate" / "_terms.py").exists()
