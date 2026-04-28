"""Tests for the GitHub release workflow."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def test_release_workflow_publishes_to_pypi_with_trusted_publishing() -> None:
    """Release workflow publishes distributions to PyPI via GitHub OIDC."""
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    pypi_publish_step = """      - name: Publish distributions to PyPI
        if: steps.release.outputs.released == 'true'
        uses: pypa/gh-action-pypi-publish@release/v1"""

    assert "id-token: write" in workflow
    assert "environment:\n      name: release" in workflow
    assert pypi_publish_step in workflow


def test_release_workflow_publishes_to_pypi_before_bundle_artifacts() -> None:
    """Release workflow uploads only Python distributions to PyPI."""
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    pypi_publish_index = workflow.index("pypa/gh-action-pypi-publish@release/v1")
    bundle_build_index = workflow.index("Build Claude bundle")
    github_release_index = workflow.index("Upload artifacts to GitHub Release")

    assert pypi_publish_index < bundle_build_index < github_release_index
