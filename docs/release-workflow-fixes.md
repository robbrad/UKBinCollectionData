# Release Workflow Fixes Applied

## Summary
Fixed the release workflow to ensure proper version bumping and release publishing from PR merge to master.

## Issues Identified

1. **Bump workflow wasn't explicitly pushing tags**
   - Commitizen action needed `push: true` parameter
   - No confirmation output of version bump

2. **Release workflow lacked validation**
   - No verification that Poetry version matches git tag
   - Could publish mismatched versions

3. **Missing pre-merge validation**
   - No check that version files are in sync before merge
   - Could lead to failed releases

4. **Inconsistent Poetry installation**
   - Some workflows used `abatilo/actions-poetry`
   - Others used `pipx install poetry`

## Changes Made

### 1. Updated `.github/workflows/bump.yml`
**Changes:**
- Added explicit Poetry installation for consistency
- Added `push: true` to commitizen action to ensure tags are pushed
- Added version output for debugging

**Why:** Ensures tags are created and pushed, triggering the release workflow

### 2. Updated `.github/workflows/release.yml`
**Changes:**
- Added `fetch-depth: 0` to checkout for full git history
- Renamed "Run image" step to "Install Poetry" for clarity
- Added version verification step to ensure Poetry version matches tag
- Split build and publish into separate steps
- Added build artifacts to GitHub release

**Why:** Prevents publishing mismatched versions and improves reliability

### 3. Created `.github/workflows/validate-release-ready.yml`
**New workflow that:**
- Validates `pyproject.toml` syntax
- Checks version consistency across files
- Validates commitizen configuration
- Runs on every PR

**Why:** Catches version sync issues before merge, preventing failed releases

### 4. Created `docs/release-workflow.md`
**Comprehensive documentation covering:**
- Complete workflow stages (PR → Merge → Release)
- Commit message format and examples
- Version numbering strategy
- Troubleshooting guide
- Manual release procedure
- Required secrets and environments

**Why:** Provides clear guidance for contributors and maintainers

### 5. Created `docs/release-workflow-diagram.md`
**Visual documentation showing:**
- ASCII flow diagrams for each stage
- Parallel workflow execution
- Decision points and error handling
- Commit message examples with version impacts
- Troubleshooting flows
- Dependency tree

**Why:** Makes the workflow easy to understand at a glance

## Complete Workflow Flow

```
1. Developer creates PR
   ↓
2. Automated tests run (behave, lint, validate)
   ↓
3. PR approved and merged to master
   ↓
4. bump.yml triggers:
   - Analyzes commits
   - Bumps version in all files
   - Creates commit "bump: version X.Y.Z"
   - Creates and pushes tag X.Y.Z
   ↓
5. release.yml triggers (on tag push):
   - Verifies version matches tag
   - Builds package
   - Creates GitHub release
   - Publishes to PyPI
   ↓
6. Release complete!
```

## Testing the Workflow

### Test 1: Version Validation
```bash
# Should pass if versions are in sync
poetry check
jq -r '.version' custom_components/uk_bin_collection/manifest.json
poetry version -s
```

### Test 2: Commit Message Format
```bash
# Valid examples:
git commit -m "feat(councils): add new council"
git commit -m "fix(selenium): handle timeout"
git commit -m "docs: update README"

# Invalid examples (will fail lint):
git commit -m "added new feature"
git commit -m "Fixed bug"
```

### Test 3: Manual Version Bump (if needed)
```bash
# Bump version
poetry version patch  # or minor/major

# Update manifest
# Edit custom_components/uk_bin_collection/manifest.json

# Commit and tag
git add .
git commit -m "bump: version X.Y.Z"
git tag X.Y.Z
git push origin master --tags
```

## Required Secrets

Ensure these are set in GitHub repository settings:

1. **PERSONAL_ACCESS_TOKEN**
   - Settings → Secrets → Actions
   - Needs: `repo` scope
   - Used by: bump.yml

2. **PYPI_API_KEY**
   - Settings → Secrets → Actions
   - Get from: pypi.org account settings
   - Used by: release.yml

3. **CODECOV_TOKEN**
   - Settings → Secrets → Actions
   - Get from: codecov.io project settings
   - Used by: test workflows

## Verification Checklist

After merging these changes:

- [ ] Verify `PERSONAL_ACCESS_TOKEN` secret is set
- [ ] Verify `PYPI_API_KEY` secret is set
- [ ] Verify `CODECOV_TOKEN` secret is set
- [ ] Check bump and release environments exist
- [ ] Test with a small PR using conventional commits
- [ ] Monitor bump workflow creates tag
- [ ] Monitor release workflow publishes to PyPI
- [ ] Verify GitHub release is created
- [ ] Check PyPI package is available

## Rollback Plan

If issues occur:

1. **Disable automatic bumping:**
   - Add `[skip ci]` to commit messages
   - Or temporarily disable bump.yml workflow

2. **Manual release:**
   - Follow manual release procedure in docs/release-workflow.md
   - Use `poetry version` and `poetry publish` directly

3. **Revert workflow changes:**
   - Git revert the workflow file changes
   - Return to previous manual process

## Next Steps

1. Merge these workflow fixes to master
2. Test with a small feature PR
3. Monitor the complete flow
4. Update team documentation if needed
5. Consider adding release notifications (Slack, Discord, etc.)

## Additional Improvements (Future)

Consider adding:
- Slack/Discord notifications on release
- Automated changelog generation
- Release candidate (RC) workflow for testing
- Automated rollback on failed releases
- Release metrics and monitoring
- Pre-release testing environment
