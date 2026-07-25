"""Tests for the GitHub release and publish workflows."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
PUBLISH_WORKFLOW = ROOT / ".github" / "workflows" / "publish.yml"


def test_release_workflow_does_not_publish_to_pypi() -> None:
    """Release workflow no longer uploads to PyPI — that moved to publish.yml."""
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "pypa/gh-action-pypi-publish" not in workflow
    assert "environment:" not in workflow


def test_release_workflow_builds_bundle_before_uploading_artifacts() -> None:
    """Release workflow builds the Claude bundle, then uploads to the GitHub Release."""
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    bundle_build_index = workflow.index("Build Claude bundle")
    github_release_index = workflow.index("Upload artifacts to GitHub Release")

    assert bundle_build_index < github_release_index


def test_publish_workflow_triggers_only_on_version_tags() -> None:
    """Publish workflow runs only on `v*` tag pushes."""
    workflow = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert "tags:" in workflow
    assert '"v*"' in workflow
    assert "branches:" not in workflow


def test_publish_workflow_uses_pypi_environment_with_oidc() -> None:
    """Publish workflow runs in the gated `pypi` environment with OIDC enabled."""
    workflow = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert "environment:\n      name: pypi" in workflow
    assert "id-token: write" in workflow


def test_publish_workflow_downloads_only_python_distributions() -> None:
    """Publish workflow downloads wheels/sdists from the Release, not the Claude bundle."""
    workflow = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    download_index = workflow.index("gh release download")
    publish_index = workflow.index("pypa/gh-action-pypi-publish@release/v1")

    assert download_index < publish_index
    assert "*.whl" in workflow
    assert "*.tar.gz" in workflow
    assert "claude-bundle" not in workflow


def test_changelog_carries_semantic_release_insertion_flag() -> None:
    """
    CHANGELOG.md must contain the insertion flag semantic-release writes at.

    `changelog.mode` defaults to `update`, which inserts new sections at this
    flag and silently no-ops without it — five releases shipped no notes that
    way (#50).
    """
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "<!-- version list -->" in changelog
