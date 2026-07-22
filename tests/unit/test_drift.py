"""Tests for disambiguate.drift — the drift-check engine."""

from __future__ import annotations

from pathlib import Path

from disambiguate.drift import run_drift_checks
from disambiguate.glossary import load_glossary


def _write(directory: Path, name: str, body: str) -> Path:
    path = directory / f"{name}.md"
    path.write_text(body, encoding="utf-8")
    return path


def _setup_glossary(tmp_path: Path) -> Path:
    glossary_dir = tmp_path / "glossary"
    glossary_dir.mkdir()
    return glossary_dir


def test_unlinked_mention_produces_one_finding(tmp_path: Path) -> None:
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    root = _write(
        tmp_path,
        "README",
        "[w](glossary/widget.md)\n",
    )
    doc = _write(
        tmp_path,
        "guide",
        "The widget spins. Later the widget stops.\n",
    )
    root.write_text(
        "[w](glossary/widget.md) [guide](guide.md)\n",
        encoding="utf-8",
    )
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    unlinked = [f for f in findings if f.rule_code == "unlinked-term"]
    assert len(unlinked) == 1
    assert unlinked[0].term == "widget"
    assert unlinked[0].path == doc
    assert unlinked[0].line == 1


def test_linked_once_silences_later_plain_mentions(tmp_path: Path) -> None:
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    root = _write(
        tmp_path,
        "README",
        "A [widget](glossary/widget.md) spins. Later the widget stops.\n",
    )
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []


def test_mention_inside_inline_code_span_is_not_drift(tmp_path: Path) -> None:
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    root = _write(
        tmp_path,
        "README",
        "[w](glossary/widget.md) [g](guide.md)\n",
    )
    _write(tmp_path, "guide", "Run the `widget` command.\n")
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []


def test_mention_inside_code_fence_is_not_drift(tmp_path: Path) -> None:
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    root = _write(
        tmp_path,
        "README",
        "[w](glossary/widget.md) [g](guide.md)\n",
    )
    _write(tmp_path, "guide", "Example:\n\n```\nwidget --help\n```\n")
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []


def test_mention_inside_markdown_link_display_text_is_not_drift(
    tmp_path: Path,
) -> None:
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    root = _write(
        tmp_path,
        "README",
        "[w](glossary/widget.md) [g](guide.md)\n",
    )
    _write(tmp_path, "guide", "See the [widget docs](https://example.com).\n")
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []


def test_mention_inside_wikilink_display_text_is_not_drift(tmp_path: Path) -> None:
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    _write(glossary_dir, "factory", "## Factory\n\nA factory.\n")
    root = _write(
        tmp_path,
        "README",
        "[w](glossary/widget.md) [f](glossary/factory.md) [g](guide.md)\n",
    )
    _write(tmp_path, "guide", "See [[factory|the widget factory]].\n")
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []


def test_matching_is_case_insensitive(tmp_path: Path) -> None:
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    root = _write(tmp_path, "README", "[w](glossary/widget.md) [g](guide.md)\n")
    _write(tmp_path, "guide", "The WIDGET spins.\n")
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f.term for f in findings if f.rule_code == "unlinked-term"] == ["widget"]


def test_matching_is_word_boundaried(tmp_path: Path) -> None:
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    root = _write(tmp_path, "README", "[w](glossary/widget.md) [g](guide.md)\n")
    _write(tmp_path, "guide", "Many widgets and midwidget things.\n")
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []


def test_compound_term_mention_is_not_a_mention_of_its_parts(tmp_path: Path) -> None:
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    _write(glossary_dir, "widget-factory", "## Widget factory\n\n[[widget]] maker.\n")
    root = _write(
        tmp_path,
        "README",
        "[w](glossary/widget.md) [wf](glossary/widget-factory.md) [g](guide.md)\n",
    )
    _write(
        tmp_path,
        "guide",
        "A [widget-factory](glossary/widget-factory.md) runs; "
        "the widget-factory hums.\n",
    )
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []


def _widget_project(tmp_path: Path, guide_text: str) -> tuple[Path, Path]:
    """Glossary with `widget` + README root linking guide.md with `guide_text`."""
    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    root = _write(tmp_path, "README", "[w](glossary/widget.md) [g](guide.md)\n")
    _write(tmp_path, "guide", guide_text)
    return glossary_dir, root


def test_inline_ignore_hint_on_same_line_silences_finding(tmp_path: Path) -> None:
    glossary_dir, root = _widget_project(
        tmp_path,
        "The widget spins. <!-- d10e: ignore[unlinked-term] widget -->\n",
    )
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []


def test_inline_ignore_hint_on_line_above_silences_finding(tmp_path: Path) -> None:
    glossary_dir, root = _widget_project(
        tmp_path,
        "<!-- d10e: ignore[unlinked-term] widget -->\nThe widget spins.\n",
    )
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []


def test_inline_ignore_hint_far_away_does_not_silence(tmp_path: Path) -> None:
    glossary_dir, root = _widget_project(
        tmp_path,
        "The widget spins.\n\n\nText.\n<!-- d10e: ignore[unlinked-term] widget -->\n",
    )
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f.term for f in findings if f.rule_code == "unlinked-term"] == ["widget"]


def test_file_level_opt_out_silences_rule_across_file(tmp_path: Path) -> None:
    glossary_dir, root = _widget_project(
        tmp_path,
        "<!-- d10e: ignore-file[unlinked-term] -->\n\nText.\n\nThe widget spins.\n",
    )
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []


def test_long_form_disambiguate_keyword_is_accepted(tmp_path: Path) -> None:
    glossary_dir, root = _widget_project(
        tmp_path,
        "The widget spins. <!-- disambiguate: ignore[unlinked-term] widget -->\n",
    )
    glossary = load_glossary(glossary_dir)
    findings = run_drift_checks(glossary, roots=[root])
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []


def test_config_ignore_silences_rule_repo_wide(tmp_path: Path) -> None:
    from disambiguate.suppressions import DriftConfig

    glossary_dir, root = _widget_project(tmp_path, "The widget spins.\n")
    glossary = load_glossary(glossary_dir)
    config = DriftConfig(ignore=["unlinked-term"], ignore_paths={})
    findings = run_drift_checks(glossary, roots=[root], config=config)
    assert [f for f in findings if f.rule_code == "unlinked-term"] == []


def test_config_ignore_paths_scopes_by_glob(tmp_path: Path) -> None:
    from disambiguate.suppressions import DriftConfig

    glossary_dir = _setup_glossary(tmp_path)
    _write(glossary_dir, "widget", "## Widget\n\nA widget.\n")
    root = _write(
        tmp_path,
        "README",
        "[w](glossary/widget.md) [g](guide.md) [o](other.md)\n",
    )
    _write(tmp_path, "guide", "The widget spins.\n")
    _write(tmp_path, "other", "The widget hums.\n")
    glossary = load_glossary(glossary_dir)
    config = DriftConfig(
        ignore=[],
        ignore_paths={"guide.md": ["unlinked-term"]},
        root=tmp_path,
    )
    findings = run_drift_checks(glossary, roots=[root], config=config)
    flagged = sorted(f.path.name for f in findings if f.rule_code == "unlinked-term")
    assert flagged == ["other.md"]


def test_load_drift_config_reads_pyproject(tmp_path: Path) -> None:
    from disambiguate.suppressions import load_drift_config

    (tmp_path / "pyproject.toml").write_text(
        "[tool.disambiguate]\n"
        'drift-ignore = ["unlinked-term"]\n'
        "[tool.disambiguate.drift-ignore-paths]\n"
        '"docs/*.md" = ["term-case"]\n',
        encoding="utf-8",
    )
    config = load_drift_config(tmp_path)
    assert config is not None
    assert config.ignore == ["unlinked-term"]
    assert config.ignore_paths == {"docs/*.md": ["term-case"]}
