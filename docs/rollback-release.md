# Rollback Release Guide

This guide explains how to rollback a release if something goes wrong.

## When to Rollback

Rollback a release if:
- ❌ Critical bug discovered after release
- ❌ Breaking change not properly documented
- ❌ Security vulnerability found
- ❌ Package doesn't work as expected

## Quick Rollback (Automated)

### Using the Rollback Workflow

1. **Go to GitHub Actions:**
   - https://github.com/robbrad/UKBinCollectionData/actions/workflows/rollback-release.yml

2. **Click "Run workflow"**

3. **Enter the version to rollback:**
   - Example: `0.155.0`
   - Format: `X.Y.Z` (no `v` prefix)

4. **Choose PyPI option:**
   - Check "Also yank from PyPI" if you want to mark it as unsuitable
   - Note: PyPI doesn't allow deletion, only yanking (marking as bad)

5. **Click "Run workflow"**

6. **Monitor the workflow:**
   - It will delete the GitHub release
   - It will delete the git tag
   - It will provide instructions for PyPI yanking

## What the Rollback Does

✅ **Deletes GitHub Release** - Removes from releases page
✅ **Deletes Git Tag** - Removes the version tag
⚠️ **PyPI Yank** - Marks as unsuitable (manual step required)
❌ **Does NOT** - Delete the bump commit from git history

## Manual Rollback Steps

If you prefer to do it manually or the workflow fails:

### 1. Delete GitHub Release

```bash
# Using GitHub CLI
gh release delete 0.155.0 --yes

# Or via web interface:
# Go to: https://github.com/robbrad/UKBinCollectionData/releases
# Find the release, click "Delete"
```

### 2. Delete Git Tag

```bash
# Delete remote tag
git push origin :refs/tags/0.155.0

# Delete local tag (optional)
git tag -d 0.155.0
```

### 3. Yank from PyPI (Optional)

PyPI doesn't allow deleting releases, but you can "yank" them:

1. Go to: https://pypi.org/manage/project/uk-bin-collection/releases/
2. Find the version (e.g., `0.155.0`)
3. Click "Options" → "Yank release"
4. Provide a reason (e.g., "Critical bug - use 0.155.1 instead")

**Note:** Yanked releases:
- Won't be installed by default with `pip install uk-bin-collection`
- Can still be installed explicitly with `pip install uk-bin-collection==0.155.0`
- Remain visible on PyPI with a "yanked" label

## Full Rollback (Including Commit)

If you want to completely remove the version bump commit:

### Option 1: Revert the Bump Commit

```bash
# Find the bump commit
git log --oneline | grep "bump: version 0.155.0"

# Revert it (creates a new commit that undoes the bump)
git revert <commit-hash>

# Push the revert
git push origin master
```

### Option 2: Reset to Previous Version (Dangerous!)

⚠️ **Warning:** This rewrites history and should only be done if no one else has pulled the changes.

```bash
# Find the commit before the bump
git log --oneline

# Reset to that commit
git reset --hard <commit-before-bump>

# Force push (dangerous!)
git push origin master --force
```

## After Rollback

### 1. Fix the Issue

- Fix the bug or problem that caused the rollback
- Test thoroughly
- Create a new PR with the fix

### 2. Create a New Release

- Merge the fix PR
- The bump workflow will create a new version (e.g., `0.155.1`)
- Announce the new version and explain what was fixed

### 3. Notify Users

Consider notifying users via:
- GitHub release notes
- Project README
- Discord/Slack/communication channels
- PyPI project description

## Rollback Workflow Details

### What It Does

1. **Validates version format** - Ensures you entered a valid version
2. **Checks if release exists** - Verifies the release is there
3. **Deletes GitHub release** - Removes from releases page
4. **Deletes git tag** - Removes from repository
5. **Provides PyPI instructions** - Guides you through yanking

### What It Doesn't Do

- ❌ Doesn't delete the bump commit
- ❌ Doesn't automatically yank from PyPI (requires manual step)
- ❌ Doesn't notify users
- ❌ Doesn't prevent re-installation of the version

### Permissions Required

The rollback workflow uses:
- `DEPLOY_KEY` - To delete git tags
- `GITHUB_TOKEN` - To delete GitHub releases
- `PYPI_API_KEY` - For PyPI operations (if needed)

All of these are already configured for your bump and release workflows.

## Troubleshooting

### "Release not found"
- Check the version number is correct
- Verify the release exists at: https://github.com/robbrad/UKBinCollectionData/releases

### "Permission denied" when deleting tag
- Verify `DEPLOY_KEY` secret is set correctly
- Check deploy key has write access

### "Cannot delete from PyPI"
- PyPI doesn't allow deletion, only yanking
- Follow the manual PyPI yank steps above

## Prevention

To avoid needing rollbacks:

1. ✅ Test thoroughly before merging
2. ✅ Use conventional commits correctly
3. ✅ Review CHANGELOG before release
4. ✅ Monitor first few installs after release
5. ✅ Have a staging/beta release process for major changes

## Emergency Contact

If you need to rollback urgently and the workflow fails:
1. Delete the GitHub release manually
2. Delete the tag manually
3. Yank from PyPI manually
4. Create an issue documenting what happened

## Example Rollback Scenario

**Scenario:** Version 0.155.0 was released but has a critical bug.

**Steps:**
1. Run rollback workflow for `0.155.0`
2. Fix the bug in a new PR
3. Merge the PR (creates `0.155.1`)
4. Update release notes for `0.155.1` explaining the fix
5. Notify users to upgrade from `0.155.0` to `0.155.1`

**Result:** 
- `0.155.0` is yanked and unavailable
- `0.155.1` is the new stable version
- Users are protected from the bug
