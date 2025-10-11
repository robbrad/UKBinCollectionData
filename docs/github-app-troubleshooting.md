# GitHub App Troubleshooting - Branch Protection

## Problem: "Protected branch update failed"

If you're getting this error, the GitHub App isn't properly configured to bypass branch protection.

## Solution Steps

### Step 1: Verify App Installation

1. Go to: https://github.com/settings/installations
2. Find your app (e.g., "UKBinCollection Release Bot")
3. Click "Configure"
4. Verify it's installed on `UKBinCollectionData` repository
5. Check that it has "Contents: Read and write" permission

### Step 2: Configure Branch Protection

Go to: https://github.com/robbrad/UKBinCollectionData/settings/branches

Click "Edit" on your `master` branch protection rule.

#### Option A: Allow App to Bypass (Recommended)

Scroll to **"Allow specified actors to bypass required pull requests"**:
- Click "Add"
- Search for your app name
- Select it
- Click "Save changes"

#### Option B: If App Doesn't Appear in Search

The app might not show up in the bypass list. Instead:

1. Temporarily disable "Require a pull request before merging"
2. Test the workflow
3. Re-enable after confirming it works

OR

1. Under "Restrict who can push to matching branches":
   - Enable it
   - Add your GitHub App
   - This allows the app to push directly

### Step 3: Verify App Permissions

Go to your app settings: https://github.com/settings/apps

1. Click on your app
2. Verify permissions:
   - **Contents**: Read and write ✅
   - **Metadata**: Read-only ✅
3. If permissions are wrong, update them
4. Go to https://github.com/settings/installations
5. Click "Configure" on your app
6. Click "Update" to refresh permissions

### Step 4: Check Secrets

Verify secrets are set correctly:

1. Go to: https://github.com/robbrad/UKBinCollectionData/settings/secrets/actions
2. Verify `APP_ID` exists
3. Verify `APP_PRIVATE_KEY` exists
4. The private key should include:
   ```
   -----BEGIN RSA PRIVATE KEY-----
   [key content]
   -----END RSA PRIVATE KEY-----
   ```

### Step 5: Test the Workflow

Create a test PR and merge it to see if it works.

## Alternative: Temporary Workaround

If you need to release immediately while fixing the app setup:

### Manual Release

```bash
# 1. Pull latest
git checkout master
git pull

# 2. Bump version
cz bump --yes --changelog

# 3. Push (you'll need to temporarily disable branch protection)
git push origin master --follow-tags
```

### Or Use Personal Access Token Temporarily

Update `.github/workflows/bump.yml`:

```yaml
- name: Checkout
  uses: actions/checkout@v5
  with:
    fetch-depth: 0
    token: ${{ secrets.PERSONAL_ACCESS_TOKEN }}
```

Then:
1. Create a PAT at: https://github.com/settings/tokens/new
2. Select scope: `repo`
3. Add as secret: `PERSONAL_ACCESS_TOKEN`
4. This will work until you fix the app setup

## Common Issues

### "Bad credentials"
- Private key not copied correctly
- Missing BEGIN/END lines
- Extra spaces or line breaks

### "Resource not accessible by integration"
- App doesn't have correct permissions
- App not installed on repository
- Need to update app permissions

### "App not found"
- APP_ID is incorrect
- App was deleted or renamed

## Still Not Working?

If none of the above works, you have two options:

### Option 1: Use Personal Access Token (Quick Fix)
See "Alternative: Temporary Workaround" above

### Option 2: Remove Branch Protection for Automation
1. Create a separate branch protection rule
2. Exclude `github-actions[bot]` from restrictions
3. This allows the workflow to push

## Need More Help?

Check the workflow logs for the exact error message and search for it in:
- GitHub Actions documentation
- GitHub App documentation
- Stack Overflow
