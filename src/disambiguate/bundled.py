"""
Load Disambiguate's generated bundled package data.

The build hook stages `disambiguate/_glossary/` and `disambiguate/_terms.py`
into built artifacts. The packaged CLI assumes those generated files exist.
"""

from __future__ import annotations

import importlib
from importlib import resources
from pathlib import Path

from .glossary import Glossary, load_glossary


def bundled_term_slugs() -> tuple[str, ...]:
    """
    Return bundled glossary slugs for the help epilog.

    Returns
    -------
    Alphabetically ordered slugs from generated `disambiguate/_terms.py`.

    Raises
    ------
    ModuleNotFoundError: generated `_terms.py` is missing.

    """
    terms_module = importlib.import_module("disambiguate._terms")
    terms: tuple[str, ...] = terms_module.TERMS
    return terms


def load_bundled_glossary() -> Glossary:
    """
    Load Disambiguate's own bundled glossary.

    Returns
    -------
    Glossary loaded from generated `disambiguate/_glossary/` package data.

    Raises
    ------
    FileNotFoundError: generated package data is missing or cannot be read.
    DuplicateSlugError: generated glossary contains duplicate slugs.

    """
    glossary_resource = resources.files("disambiguate") / "_glossary"
    if not glossary_resource.is_dir():
        raise FileNotFoundError(
            f"Bundled glossary directory not found: {glossary_resource}"
        )

    # resources.files returns a Traversable; as_file materializes a real path
    # for zipped distributions while staying cheap for unpacked installs.
    with resources.as_file(glossary_resource) as glossary_dir:
        return load_glossary(Path(glossary_dir))
