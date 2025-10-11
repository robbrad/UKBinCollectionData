# Release Workflow Documentation

## Overview
This document describes the complete release workflow from pull request to published release.

## Workflow Stages

### 1. Pull Request Stage
**Triggers:** When a PR is opened/updated targeting `master` branch

**Workflows that run:**
- `behave_pull_request.yml` - Runs tests on changed councils
- `lint.yml` - Validates commit messages follow conventional commits
- `validate-release-ready.yml` - Validates pyproject.toml and commit messages
- `hacs_validation.yml` - Validates Home Assistant integration

**What happens:**
- Unit tests run on Python 3.12
- Integration tests run only for changed council files
- Parity check ensures councils, input.json, and feature files are in sync
- Commit messages are validated against conventional commits format
- pyproject.toml is validated

**Requirements to merge:**
- All tests must pass
- Commit messages must follow conventional commits format
- Code must pass linting

### 2. Merge to Master Stage
**Triggers:** When PR is merged to `master` branch

**Workflow that runs:**
- `bump.yml` - Automatically bumps version and creates release

**What happens:**
1. Commitizen analyzes commit messages since last tag
2. Determines version bump type (major/minor/patch) based on conventional commits:
   - `feat:` → minor version bump
   - `fix:` → patch version bump
   - `BREAKING CHANGE:` → major version bump
3. Updates version in all configured files:
   - `pyproject.toml`
   - `custom_components/uk_bin_collection/manifest.json`
   - `custom_components/uk_bin_collection/const.py`
4. Updates CHANGELOG.md
5. Creates a commit with message `bump: version X.Y.Z`
6. Creates and pushes a git tag `X.Y.Z`
7. Pushes the commit and tag to master

**Note:** The bump workflow is skipped if the commit message starts with `bump:` to prevent infinite loops.

### 3. Release Stage
**Triggers:** When a tag is pushed (automatically by bump workflow)

**Workflow that runs:**
- `release.yml` - Publishes the release

**What happens:**
1. Checks out the tagged commit
2. Verifies the Poetry version matches the git tag
3. Builds the Python package with Poetry
4. Creates a GitHub release with auto-generated release notes
5. Publishes the package to PyPI
6. Attaches build artifacts to the GitHub release

## Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature (minor version bump)
- `fix`: Bug fix (patch version bump)
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples
```
feat(councils): add support for Manchester City Council

Implements web scraping for Manchester bin collection data.
Includes integration tests and documentation.
```

```
fix(selenium): handle timeout errors gracefully

Adds retry logic for Selenium timeouts to improve reliability
on slower connections.
```

```
feat(api)!: change API response format

BREAKING CHANGE: API now returns ISO 8601 dates instead of UK format.
Clients must update their date parsing logic.
```

## Version Numbering

Following Semantic Versioning (SemVer):
- `MAJOR.MINOR.PATCH` (e.g., `0.152.10`)
- Major version 0 indicates pre-1.0 development
- PATCH: Bug fixes, minor changes
- MINOR: New features, backward compatible
- MAJOR: Breaking changes

## Troubleshooting

### Version bump didn't trigger
**Cause:** Commit message doesn't follow conventional commits format
**Solution:** Ensure commits use `feat:`, `fix:`, etc. prefixes

### Release workflow didn't run
**Cause:** Tag wasn't created by bump workflow
**Solution:** Check bump workflow logs, ensure GITHUB_TOKEN has proper permissions

### Version mismatch error
**Cause:** Version files out of sync
**Solution:** Commitizen automatically syncs all version files configured in pyproject.toml

### PyPI publish failed
**Cause:** `PYPI_API_KEY` secret not set or invalid
**Solution:** Update the secret in repository settings

### Bump workflow fails with permission error
**Cause:** Protected branch prevents direct pushes or GitHub App not configured
**Solution:** 
1. Verify `APP_ID` and `APP_PRIVATE_KEY` secrets are set correctly
2. Ensure the GitHub App is installed on the repository
3. Check that the app has "Contents: Read and write" permission
4. Verify the private key includes the BEGIN/END lines

## Manual Release (Emergency)

If automated release fails, you can manually release:

```bash
# 1. Bump version with Commitizen
cz bump --yes --changelog

# 2. Push changes and tags
git push origin master --follow-tags

# 3. Or manually build and publish
poetry build
poetry publish
```

## Secrets Required

### Repository Secrets
- `APP_ID`: GitHub App ID for bypassing branch protection
- `APP_PRIVATE_KEY`: GitHub App private key (entire `.pem` file contents)
- `PYPI_API_KEY`: PyPI API token for publishing packages
- `CODECOV_TOKEN`: Codecov token for test coverage reporting (optional)

### GitHub App Setup
The workflow uses a GitHub App to authenticate and bypass branch protection. This is more secure than personal access tokens and doesn't expire. See the [Setup Checklist](./release-workflow-setup-checklist.md#github-app-setup-for-protected-branches) for detailed setup instructions.

## Workflow Files

- `.github/workflows/behave_pull_request.yml` - PR testing
- `.github/workflows/lint.yml` - Commit message linting
- `.github/workflows/validate-release-ready.yml` - Pre-merge validation
- `.github/workflows/bump.yml` - Automated version bumping and tagging
- `.github/workflows/release.yml` - Release publishing to PyPI and GitHub
- `.github/workflows/hacs_validation.yml` - HACS validation
- `.github/workflows/codeql-analysis.yml` - Security scanning

## Best Practices

1. **Always use conventional commits** - This ensures proper version bumping
2. **Test locally before PR** - Run `make pre-build` to catch issues early
3. **Keep PRs focused** - Smaller PRs are easier to review and test
4. **Update documentation** - Keep wiki and docs in sync with code changes
5. **Monitor workflow runs** - Check GitHub Actions tab after merging
6. **Verify releases** - Check PyPI and GitHub releases after publishing
7. **Let Commitizen handle versions** - Don't manually edit version files

## How It Works

The workflow is fully automated:

1. **Developer** creates PR with conventional commits
2. **CI** validates commits and runs tests
3. **Merge** to master triggers bump workflow
4. **Commitizen** analyzes commits, updates versions, creates tag
5. **Tag push** triggers release workflow
6. **Release** publishes to PyPI and creates GitHub release

No manual intervention needed!
