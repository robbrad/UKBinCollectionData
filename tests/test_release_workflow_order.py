"""Regression checks for safe core/component publication ordering."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_core_is_verified_before_manifest_bearing_branch_is_pushed() -> None:
    workflow = (ROOT / ".github" / "workflows" / "bump.yml").read_text(encoding="utf-8")

    publish = workflow.index("name: Publish core to PyPI before repository writes")
    verify = workflow.index(
        "name: Verify published core bytes before repository writes"
    )
    repository_push = workflow.index("git push --atomic origin master")

    assert publish < verify < repository_push
    assert "--pypi-json dist/pypi-release.json" in workflow[verify:repository_push]
    push_step = workflow[
        workflow.index("name: Push installable release commit and tag") :
    ]
    assert push_step.count("git push") == 1
    assert "refs/tags/${{ steps.bump.outputs.version }}" in push_step


def test_tag_release_cannot_publish_or_load_pypi_credentials() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "poetry publish" not in workflow
    assert "PYPI_API_KEY" not in workflow
    assert "Verify pre-published exact core artifact from PyPI" in workflow


def test_prepublication_and_tag_rebuild_use_same_reproducible_epoch() -> None:
    bump = (ROOT / ".github" / "workflows" / "bump.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    marker = "SOURCE_DATE_EPOCH=315532800"
    assert bump.count(marker) == 1
    assert release.count(marker) == 1
