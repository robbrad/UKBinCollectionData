# Release Workflow Setup Summary

## What You Need to Do

Your release workflow has been updated to use a GitHub App for secure, automated releases. Here's what you need to do to get it working:

### 1. Create GitHub App (5 minutes)

Follow the detailed guide: [GitHub App Setup Guide](./github-app-setup.md)

**Quick steps:**
1. Go to https://github.com/settings/apps/new
2. Fill in:
   - Name: `UKBinCollection Release Bot` (or similar unique name)
   - Homepage: `https://github.com/robbrad/UKBinCollectionData`
   - Uncheck "Webhook Active"
   - Permissions: **Contents** = Read and write
3. Click "Create GitHub App"
4. Click "Install App" → Select your repository
5. Generate a private key (downloads a `.pem` file)

### 2. Add Secrets to Repository (2 minutes)

Go to: https://github.com/robbrad/UKBinCollectionData/settings/secrets/actions

Add two secrets:

**APP_ID**
- Value: The App ID shown at top of app settings (e.g., `123456`)

**APP_PRIVATE_KEY**
- Value: Entire contents of the `.pem` file
- Include the `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines

### 3. Test It (5 minutes)

1. Create a test branch:
   ```bash
   git checkout -b test/release-workflow
   ```

2. Make a small change with a conventional commit:
   ```bash
   echo "# Test" >> README.md
   git add README.md
   git commit -m "fix: test release workflow"
   git push origin test/release-workflow
   ```

3. Create and merge a PR on GitHub

4. Watch the workflows run:
   - Bump workflow should run and create a tag
   - Release workflow should publish to PyPI

5. Verify:
   - Check https://github.com/robbrad/UKBinCollectionData/releases
   - Check https://pypi.org/project/uk-bin-collection/

## What Changed

### Workflows Updated
- ✅ `.github/workflows/bump.yml` - Now uses GitHub App token
- ✅ `.github/workflows/release.yml` - Cleaned up
- ✅ `.github/workflows/validate-release-ready.yml` - Simplified

### Documentation Updated
- ✅ `docs/release-workflow.md` - Main documentation
- ✅ `docs/release-workflow-setup-checklist.md` - Setup checklist
- ✅ `docs/release-quick-reference.md` - Quick reference
- ✅ `docs/github-app-setup.md` - **NEW** - Detailed GitHub App guide
- ✅ `docs/release-workflow-migration.md` - Migration guide

### Configuration Updated
- ✅ `pyproject.toml` - Enhanced Commitizen config

## How It Works Now

```
1. Developer creates PR with conventional commits (feat:, fix:, etc.)
2. CI validates commits and runs tests
3. PR gets merged to master
4. Bump workflow automatically:
   - Analyzes commits with Commitizen
   - Updates version in all files
   - Updates CHANGELOG.md
   - Creates commit and tag
   - Pushes to master (using GitHub App to bypass protection)
5. Release workflow automatically:
   - Builds package
   - Publishes to PyPI
   - Creates GitHub release
```

**Everything is automated after merge!**

## Benefits

✅ **More secure** - GitHub App instead of personal token
✅ **No expiration** - Tokens auto-refresh
✅ **Fully automated** - No manual steps after PR merge
✅ **Version syncing** - Commitizen handles all version files
✅ **Better changelog** - Auto-generated from commits
✅ **Simpler** - Fewer secrets to manage

## Troubleshooting

### Bump workflow fails with "Bad credentials"
- Check that `APP_PRIVATE_KEY` includes the full key with BEGIN/END lines
- Verify no extra spaces or line breaks were added

### Bump workflow fails with "Resource not accessible"
- Verify the GitHub App has "Contents: Read and write" permission
- Check that the app is installed on the repository

### Release didn't trigger
- Check if the tag was created (look at bump workflow logs)
- Verify the tag follows the format `X.Y.Z` (no `v` prefix)

## Need Help?

- 📖 [Full Documentation](./release-workflow.md)
- 🔧 [GitHub App Setup Guide](./github-app-setup.md)
- ✅ [Setup Checklist](./release-workflow-setup-checklist.md)
- ⚡ [Quick Reference](./release-quick-reference.md)

## Next Steps

1. ✅ Complete the GitHub App setup
2. ✅ Add the secrets to your repository
3. ✅ Test with a small PR
4. ✅ Monitor the first few releases
5. ✅ Remove old `PERSONAL_ACCESS_TOKEN` if you had one
6. ✅ Update team documentation

That's it! Your release workflow is now simplified and more secure.
