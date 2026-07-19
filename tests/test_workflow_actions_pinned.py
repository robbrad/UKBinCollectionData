"""Supply-chain checks for GitHub Actions workflow dependencies."""

from pathlib import Path
import re

WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"
USES_PATTERN = re.compile(r"\buses:\s*[\"']?([^\"'\s#]+)")
FULL_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def test_external_actions_are_pinned_to_full_commit_shas() -> None:
    """Reject mutable tags, branches, and abbreviated commit references."""

    violations: list[str] = []

    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        for line_number, line in enumerate(
            workflow.read_text(encoding="utf-8").splitlines(), start=1
        ):
            match = USES_PATTERN.search(line)
            if not match:
                continue

            action = match.group(1)
            if action.startswith("./"):
                continue

            _, separator, revision = action.rpartition("@")
            if not separator or not FULL_COMMIT_PATTERN.fullmatch(revision):
                violations.append(f"{workflow.name}:{line_number}: {action}")

    assert not violations, "External actions must use full commit SHAs:\n" + "\n".join(
        violations
    )
