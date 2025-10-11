# Deploy Key Setup Guide

Since the GitHub App bypass feature isn't available on your plan, we'll use a deploy key instead. This works on all GitHub plans and can bypass branch protection.

## Step 1: Generate SSH Key Pair

On your local machine (Windows), open PowerShell and run:

```powershell
ssh-keygen -t ed25519 -C "github-actions-deploy-key" -f ukbcd-deploy-key -N ""
```

This creates two files:
- `ukbcd-deploy-key` (private key)
- `ukbcd-deploy-key.pub` (public key)

## Step 2: Add Public Key to Repository

1. Go to: https://github.com/robbrad/UKBinCollectionData/settings/keys

2. Click **"Add deploy key"**

3. Fill in:
   - **Title**: `Release Workflow Deploy Key`
   - **Key**: Paste the contents of `ukbcd-deploy-key.pub`
   - **✅ Allow write access** - IMPORTANT: Check this box!

4. Click **"Add key"**

## Step 3: Add Private Key as Secret

1. Go to: https://github.com/robbrad/UKBinCollectionData/settings/secrets/actions

2. Click **"New repository secret"**

3. Fill in:
   - **Name**: `DEPLOY_KEY`
   - **Value**: Paste the entire contents of `ukbcd-deploy-key` (the private key, not .pub)

4. Click **"Add secret"**

## Step 4: Update Branch Protection

Deploy keys with write access can bypass branch protection automatically, but you need to ensure:

1. Go to: https://github.com/robbrad/UKBinCollectionData/settings/branch_protection_rules

2. Edit your master branch rule

3. Make sure **"Do not allow bypassing the above settings"** is UNCHECKED
   - Or if you see **"Include administrators"**, UNCHECK it

4. Save changes

## Step 5: Clean Up

After adding the keys to GitHub, delete the local key files:

```powershell
Remove-Item ukbcd-deploy-key
Remove-Item ukbcd-deploy-key.pub
```

## Step 6: Remove Old Secrets (Optional)

Since we're not using the GitHub App anymore, you can remove:
- `APP_ID`
- `APP_PRIVATE_KEY`

Or keep them for future use.

## Test It

1. Create a test PR with a conventional commit
2. Merge it
3. Watch the bump workflow run
4. It should now successfully push to master

## How It Works

- Deploy keys with write access can push to protected branches
- The SSH key authenticates the workflow
- No need for GitHub App or PAT
- Works on all GitHub plans (Free, Pro, Team, Enterprise)

## Troubleshooting

### "Permission denied (publickey)"
- Check that `DEPLOY_KEY` secret contains the private key (not the .pub file)
- Verify the deploy key is added to the repository with write access

### Still getting "Protected branch update failed"
- Ensure "Allow write access" is checked on the deploy key
- Uncheck "Do not allow bypassing the above settings" in branch protection

### "Host key verification failed"
- This shouldn't happen with GitHub, but if it does, the workflow will handle it automatically

## Security Notes

✅ Deploy key only has access to this one repository
✅ Can be revoked anytime from repository settings
✅ More secure than personal access tokens
✅ Doesn't expire

## Alternative: Personal Access Token

If deploy keys don't work, you can use a PAT:

1. Create token at: https://github.com/settings/tokens/new
2. Select scope: `repo`
3. Add as secret: `PERSONAL_ACCESS_TOKEN`
4. Update workflow to use `token: ${{ secrets.PERSONAL_ACCESS_TOKEN }}`

But deploy keys are preferred for single-repository automation.
