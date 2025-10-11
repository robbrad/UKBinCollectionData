# Release Workflow Setup Checklist

Use this checklist to verify your simplified release workflow is properly configured.

## GitHub Repository Settings

### GitHub App Setup (for protected branches)
- [ ] Create a GitHub App
  - Go to: https://github.com/settings/apps/new
  - Name: `UKBinCollection Release Bot` (must be unique)
  - Homepage URL: `https://github.com/robbrad/UKBinCollectionData`
  - Uncheck "Active" under Webhook
  - Repository permissions:
    - **Contents**: Read and write
    - **Metadata**: Read-only (auto-selected)
  - Where can this be installed: "Only on this account"
  - Click "Create GitHub App"

- [ ] Install the app on your repository
  - Click "Install App" in left sidebar
  - Click "Install" next to your account
  - Select "Only select repositories"
  - Choose `UKBinCollectionData`
  - Click "Install"

- [ ] Generate and save credentials
  - In app settings, scroll to "Private keys"
  - Click "Generate a private key"
  - Save the downloaded `.pem` file securely
  - Note your **App ID** (shown at top of settings page)

### Secrets Configuration
- [ ] `APP_ID` is set
  - Path: Settings → Secrets and variables → Actions → Repository secrets
  - Value: Your GitHub App ID (e.g., `123456`)

- [ ] `APP_PRIVATE_KEY` is set
  - Path: Settings → Secrets and variables → Actions → Repository secrets
  - Value: Entire contents of the `.pem` file
  - Include the `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines

- [ ] `PYPI_API_KEY` is set
  - Path: Settings → Secrets and variables → Actions → Repository secrets
  - Get from: https://pypi.org/manage/account/token/
  - Scope: Project-specific or account-wide
  - Test: Should allow publishing packages

- [ ] `CODECOV_TOKEN` is set (optional)
  - Path: Settings → Secrets and variables → Actions → Repository secrets
  - Get from: https://codecov.io/gh/robbrad/UKBinCollectionData/settings
  - Test: Should allow uploading coverage reports

### Branch Protection Rules
- [ ] `master` branch is protected
  - Path: Settings → Branches → Add rule
  - Branch name pattern: `master`
  - Recommended settings:
    - [x] Require a pull request before merging
    - [x] Require status checks to pass before merging
    - [x] Require branches to be up to date before merging

### Actions Permissions
- [ ] Workflows have write permissions
  - Path: Settings → Actions → General → Workflow permissions
  - Select: "Read and write permissions"
  - [x] Allow GitHub Actions to create and approve pull requests

## Local Configuration

### pyproject.toml
- [ ] Version is set correctly
  ```toml
  [tool.poetry]
  version = "X.Y.Z"
  ```

- [ ] Commitizen is configured
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

## Workflow Files

### Required Workflows
- [ ] `.github/workflows/behave_pull_request.yml` exists
- [ ] `.github/workflows/lint.yml` exists
- [ ] `.github/workflows/validate-release-ready.yml` exists
- [ ] `.github/workflows/bump.yml` exists (simplified)
- [ ] `.github/workflows/release.yml` exists
- [ ] `.github/workflows/hacs_validation.yml` exists

### Workflow Configuration
- [ ] `bump.yml` uses `GITHUB_TOKEN`
  ```yaml
  token: ${{ secrets.GITHUB_TOKEN }}
  ```

- [ ] `bump.yml` runs `cz bump --yes --changelog`
  ```yaml
  - name: Bump version and create tag
    run: cz bump --yes --changelog
  ```

- [ ] `release.yml` uses `PYPI_API_KEY`
  ```yaml
  poetry config pypi-token.pypi "${{ secrets.PYPI_API_KEY }}"
  ```

## Testing

### Pre-Merge Testing
- [ ] Create a test branch
  ```bash
  git checkout -b test/release-workflow
  ```

- [ ] Make a small change with conventional commit
  ```bash
  echo "# Test" >> README.md
  git add README.md
  git commit -m "fix: test release workflow"
  ```

- [ ] Push and create PR
  ```bash
  git push origin test/release-workflow
  # Create PR on GitHub
  ```

- [ ] Verify workflows run:
  - [ ] `behave_pull_request.yml` runs
  - [ ] `lint.yml` runs
  - [ ] `validate-release-ready.yml` runs
  - [ ] All checks pass

### Post-Merge Testing
- [ ] Merge the test PR
- [ ] Verify `bump.yml` runs automatically
- [ ] Check workflow logs:
  - [ ] Commitizen analyzed commits
  - [ ] Version was bumped in all files
  - [ ] CHANGELOG.md was updated
  - [ ] Commit was created with message `bump: version X.Y.Z`
  - [ ] Tag was created and pushed
  - [ ] No errors in logs

- [ ] Verify `release.yml` runs automatically
- [ ] Check workflow logs:
  - [ ] Version verification passed
  - [ ] Package was built
  - [ ] GitHub release was created
  - [ ] PyPI publish succeeded

### Verification
- [ ] Check GitHub releases page
  - URL: https://github.com/robbrad/UKBinCollectionData/releases
  - Latest release should be visible
  - Release notes should be auto-generated
  - Build artifacts should be attached

- [ ] Check PyPI package page
  - URL: https://pypi.org/project/uk-bin-collection/
  - Latest version should be available
  - Package should be installable:
    ```bash
    pip install uk-bin-collection==X.Y.Z
    ```

- [ ] Check version files are synced
  ```bash
  # All should show the same version
  poetry version -s
  jq -r '.version' custom_components/uk_bin_collection/manifest.json
  grep INPUT_JSON_URL custom_components/uk_bin_collection/const.py
  ```

## Rollback Plan

If something goes wrong:

### Delete Bad Release
```bash
# Delete tag locally
git tag -d X.Y.Z

# Delete tag remotely
git push origin :refs/tags/X.Y.Z

# Delete GitHub release manually on GitHub
```

### Manual Release
```bash
# Bump version with Commitizen
cz bump --yes --changelog

# Push changes and tags
git push origin master --follow-tags

# Or manually build and publish
poetry build
poetry publish
```

## Maintenance

### Regular Checks
- [ ] Quarterly: Verify PYPI_API_KEY hasn't expired
- [ ] Quarterly: Update workflow actions to latest versions
- [ ] Quarterly: Review and update documentation

### Action Updates
Check for updates to GitHub Actions:
- `actions/checkout@v5` → Check for newer version
- `actions/setup-python@v6` → Check for newer version
- `abatilo/actions-poetry@v4.0.0` → Check for newer version
- `ncipollo/release-action@v1` → Check for newer version

## Support

If you encounter issues:

1. Check workflow logs in GitHub Actions tab
2. Review documentation in `docs/release-workflow.md`
3. Verify GITHUB_TOKEN has write permissions
4. Ensure conventional commits are used
5. Check Commitizen configuration in pyproject.toml

## Sign-Off

- [ ] All checklist items completed
- [ ] Test release successful
- [ ] Documentation reviewed

**Completed by:** _______________  
**Date:** _______________
