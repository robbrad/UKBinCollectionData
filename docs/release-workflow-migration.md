# Release Workflow Migration Guide

## Overview

The release workflow has been simplified to use Commitizen and GITHUB_TOKEN, eliminating complexity and manual steps.

## What Changed

### Before (Complex)
- Bump workflow created PRs for version bumps
- Required PERSONAL_ACCESS_TOKEN secret
- Manual PR review and merge for version bumps
- Separate environments with approvals
- Manual version file syncing
- Multiple validation steps

### After (Simplified)
- Bump workflow directly commits and tags on master
- Uses built-in GITHUB_TOKEN
- Fully automated after PR merge
- No environment approvals needed
- Commitizen auto-syncs all version files
- Streamlined validation

## Key Improvements

### 1. Removed PERSONAL_ACCESS_TOKEN Requirement
- **Before**: Required creating and managing a personal access token
- **After**: Uses built-in `GITHUB_TOKEN` with proper permissions
- **Benefit**: One less secret to manage and rotate

### 2. Eliminated Bump PRs
- **Before**: Bump workflow created a PR that needed manual merge
- **After**: Bump workflow directly commits to master after PR merge
- **Benefit**: Faster releases, no manual intervention

### 3. Automatic Version Syncing
- **Before**: Manual checks to ensure version files stayed in sync
- **After**: Commitizen automatically updates all configured files
- **Benefit**: No version mismatch errors

### 4. Simplified Configuration
- **Before**: Complex environment setup with approvals
- **After**: Simple workflow permissions
- **Benefit**: Easier to set up and maintain

### 5. Better CHANGELOG Management
- **Before**: Manual or semi-automated changelog updates
- **After**: Commitizen automatically generates changelog from commits
- **Benefit**: Consistent, automated changelog

## Migration Steps

### 1. Set Up GitHub App
Follow the [GitHub App Setup Guide](./github-app-setup.md) to:
- Create a GitHub App
- Install it on your repository
- Generate a private key
- Add `APP_ID` and `APP_PRIVATE_KEY` secrets

### 2. Update Secrets
```bash
# Add (new requirements)
+ APP_ID
+ APP_PRIVATE_KEY

# Keep (still required)
- PYPI_API_KEY
- CODECOV_TOKEN (optional)

# Remove (no longer needed)
- PERSONAL_ACCESS_TOKEN (if you had one)
```

### 3. Update Workflow Permissions
Ensure Settings → Actions → General → Workflow permissions:
- Select "Read and write permissions"
- Enable "Allow GitHub Actions to create and approve pull requests"

### 4. Remove Environments (Optional)
The `bump` and `release` environments are no longer required, but can be kept if you want manual approval gates.

### 5. Update pyproject.toml
Ensure Commitizen configuration includes:
```toml
[tool.commitizen]
name = "cz_conventional_commits"
version_provider = "poetry"
version_scheme = "semver"
major_version_zero = true
tag_format = "$version"
update_changelog_on_bump = true
version_files = [
    "custom_components/uk_bin_collection/manifest.json:version",
    "custom_components/uk_bin_collection/manifest.json:requirements",
    "custom_components/uk_bin_collection/const.py:INPUT_JSON_URL"
]
```

### 6. Test the New Workflow
1. Create a test branch with a conventional commit
2. Open and merge a PR
3. Watch the automated bump and release workflows
4. Verify the release appears on PyPI and GitHub

## Workflow Comparison

### Old Workflow
```
PR → Tests → Merge → Bump Workflow → Bump PR → Manual Review → Merge Bump PR → Tag → Release
```

### New Workflow
```
PR → Tests → Merge → Bump (auto) → Tag (auto) → Release (auto)
```

## File Changes

### Modified Files
- `.github/workflows/bump.yml` - Simplified to direct commit/tag
- `.github/workflows/release.yml` - Cleaned up and uses GITHUB_TOKEN
- `.github/workflows/validate-release-ready.yml` - Removed version sync checks
- `pyproject.toml` - Enhanced Commitizen configuration
- `docs/release-workflow.md` - Updated documentation
- `docs/release-workflow-setup-checklist.md` - Simplified checklist
- `docs/release-quick-reference.md` - Updated quick reference

### New Files
- `docs/release-workflow-migration.md` - This file

## Rollback Plan

If you need to rollback to the old workflow:

1. Revert the workflow files:
   ```bash
   git revert <commit-hash>
   ```

2. Re-add PERSONAL_ACCESS_TOKEN secret

3. Recreate bump and release environments

## Benefits Summary

✅ Fewer secrets to manage
✅ Faster release process
✅ No manual intervention needed
✅ Automatic version syncing
✅ Better changelog generation
✅ Simpler configuration
✅ Easier to understand and maintain

## Support

If you encounter issues:
1. Check workflow logs in GitHub Actions
2. Review `docs/release-workflow.md`
3. Verify GITHUB_TOKEN permissions
4. Ensure conventional commits are used
5. Check Commitizen configuration

## Next Steps

1. Review the updated documentation
2. Test the new workflow with a small change
3. Monitor the first few automated releases
4. Update team documentation and training
5. Remove old PERSONAL_ACCESS_TOKEN secret

## Questions?

See the full documentation:
- [Release Workflow](./release-workflow.md)
- [Setup Checklist](./release-workflow-setup-checklist.md)
- [Quick Reference](./release-quick-reference.md)
