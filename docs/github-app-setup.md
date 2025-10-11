# GitHub App Setup Guide

This guide walks you through creating and configuring a GitHub App to allow the release workflow to bypass branch protection rules.

## Why Use a GitHub App?

✅ **More secure** - Fine-grained permissions, not tied to a user account
✅ **No expiration** - Tokens are automatically refreshed
✅ **Better audit trail** - Shows as the app, not a personal account
✅ **Team-friendly** - Won't break if someone leaves the team
✅ **Built-in bypass** - Can push to protected branches

## Step-by-Step Setup

### Step 1: Create the GitHub App

1. **Navigate to GitHub App settings:**
   - Personal account: https://github.com/settings/apps/new
   - Organization: https://github.com/organizations/YOUR_ORG/settings/apps/new

2. **Fill in the basic information:**
   - **GitHub App name**: `UKBinCollection Release Bot` (must be globally unique)
     - If taken, try: `UKBinCollection-Release-Bot-YourUsername`
   - **Homepage URL**: `https://github.com/robbrad/UKBinCollectionData`
   - **Description** (optional): `Automated release workflow for UK Bin Collection Data`

3. **Configure webhook:**
   - **Uncheck** "Active" under "Webhook"
   - We don't need webhooks for this use case

4. **Set repository permissions:**
   - **Contents**: `Read and write` ✅ (Required - to push commits and tags)
   - **Metadata**: `Read-only` (Automatically selected)
   - **Pull requests**: `Read and write` (Optional - for future features)

5. **Where can this GitHub App be installed?**
   - Select: **"Only on this account"**

6. **Click "Create GitHub App"**

### Step 2: Install the App

1. After creation, you'll see the app settings page
2. Click **"Install App"** in the left sidebar
3. Click **"Install"** next to your account/organization name
4. Choose installation scope:
   - Select **"Only select repositories"**
   - Check `UKBinCollectionData`
5. Click **"Install"**

### Step 3: Generate Private Key

1. Go back to the app settings page (Settings → Developer settings → GitHub Apps → Your App)
2. Scroll down to the **"Private keys"** section
3. Click **"Generate a private key"**
4. A `.pem` file will download automatically
5. **Save this file securely** - you'll need it in the next step

### Step 4: Get Your App Credentials

You need two pieces of information:

#### App ID
- Found at the top of your app settings page
- Example: `123456`
- Copy this number

#### Private Key
- Open the downloaded `.pem` file in a text editor
- Copy the **entire contents**, including:
  ```
  -----BEGIN RSA PRIVATE KEY-----
  [long string of characters]
  -----END RSA PRIVATE KEY-----
  ```

### Step 5: Add Secrets to Repository

1. Go to your repository: https://github.com/robbrad/UKBinCollectionData
2. Navigate to: **Settings → Secrets and variables → Actions**
3. Click **"New repository secret"**

#### Add APP_ID Secret
- **Name**: `APP_ID`
- **Value**: Your App ID (e.g., `123456`)
- Click "Add secret"

#### Add APP_PRIVATE_KEY Secret
- **Name**: `APP_PRIVATE_KEY`
- **Value**: Paste the entire contents of the `.pem` file
- **Important**: Include the `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines
- Click "Add secret"

### Step 6: Verify Setup

1. The workflow is already configured to use these secrets
2. Test by merging a PR with a conventional commit message
3. Check the bump workflow logs to verify it runs successfully

## Troubleshooting

### "Bad credentials" error
- **Cause**: Private key not copied correctly
- **Solution**: Re-copy the entire `.pem` file contents, including BEGIN/END lines

### "Resource not accessible by integration" error
- **Cause**: App doesn't have correct permissions
- **Solution**: 
  1. Go to app settings
  2. Check "Contents" permission is set to "Read and write"
  3. Reinstall the app if needed

### "App not installed" error
- **Cause**: App not installed on the repository
- **Solution**: Go to https://github.com/settings/installations and install it

### Workflow still fails with permission error
- **Cause**: Secrets not set correctly
- **Solution**: 
  1. Verify `APP_ID` is just the number (no quotes)
  2. Verify `APP_PRIVATE_KEY` includes the full key with headers
  3. Check for extra spaces or line breaks

## Security Best Practices

✅ **Never commit** the `.pem` file to your repository
✅ **Store the `.pem` file** securely (password manager or secure vault)
✅ **Rotate keys** if compromised (generate new private key)
✅ **Review app permissions** periodically
✅ **Monitor app activity** in audit logs

## Managing the App

### View App Activity
- Go to: Settings → Developer settings → GitHub Apps → Your App
- Click "Advanced" tab to see delivery logs

### Regenerate Private Key
1. Go to app settings
2. Scroll to "Private keys"
3. Click "Generate a private key"
4. Update the `APP_PRIVATE_KEY` secret in your repository

### Uninstall/Reinstall
- Go to: https://github.com/settings/installations
- Click "Configure" next to your app
- Adjust repository access or uninstall

## Alternative: Using a Personal Access Token

If you prefer not to use a GitHub App, you can use a Personal Access Token instead:

1. Create a token at: https://github.com/settings/tokens/new
2. Select scope: `repo` (Full control of private repositories)
3. Add as secret: `BUMP_TOKEN`
4. Update workflow to use `${{ secrets.BUMP_TOKEN }}` instead of the app token

However, GitHub Apps are recommended for production use.

## Next Steps

Once setup is complete:
1. ✅ Test the workflow with a small PR
2. ✅ Monitor the first few releases
3. ✅ Document the app for your team
4. ✅ Set up monitoring/alerts for workflow failures

## Support

If you encounter issues:
- Check the [troubleshooting section](#troubleshooting) above
- Review workflow logs in GitHub Actions
- See the [main workflow documentation](./release-workflow.md)
