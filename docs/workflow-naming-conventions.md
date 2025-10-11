# Workflow Naming Conventions

All GitHub Actions workflows now follow a consistent naming pattern for better organization and clarity.

## Naming Pattern

**Format:** `[Category] - [Action/Description]`

This makes it easy to:
- Group related workflows in the GitHub Actions UI
- Understand what each workflow does at a glance
- Sort workflows logically

## Workflow Categories

### 🚀 Release Workflows
Workflows related to versioning and publishing releases.

| Workflow File | Name | Purpose |
|--------------|------|---------|
| `bump.yml` | **Release - Bump Version** | Analyzes commits, bumps version, creates tag |
| `release.yml` | **Release - Publish to PyPI** | Builds and publishes package to PyPI |
| `rollback-release.yml` | **Release - Rollback** | Rollback a bad release (manual trigger) |

### ✅ PR Workflows
Workflows that run on pull requests to validate changes.

| Workflow File | Name | Purpose |
|--------------|------|---------|
| `behave_pull_request.yml` | **PR - Test Councils** | Tests changed council scrapers |
| `lint.yml` | **PR - Lint Commit Messages** | Validates conventional commits format |
| `validate-release-ready.yml` | **PR - Validate Release Ready** | Validates pyproject.toml and config |
| `hacs_validation.yml` | **PR - Validate HACS** | Validates Home Assistant integration |

### ⏰ Scheduled Workflows
Workflows that run on a schedule.

| Workflow File | Name | Purpose |
|--------------|------|---------|
| `behave_schedule.yml` | **Scheduled - Test All Councils** | Nightly full test of all councils |

### 🏗️ Build Workflows
Workflows that build artifacts.

| Workflow File | Name | Purpose |
|--------------|------|---------|
| `docker-image.yml` | **Build - Docker Image** | Builds Docker images |

### 📦 Deploy Workflows
Workflows that deploy or publish content.

| Workflow File | Name | Purpose |
|--------------|------|---------|
| `wiki.yml` | **Deploy - Wiki** | Deploys wiki documentation |

### 🔒 Security Workflows
Workflows for security scanning.

| Workflow File | Name | Purpose |
|--------------|------|---------|
| `codeql-analysis.yml` | **CodeQL** | Security code scanning |

## Benefits of Consistent Naming

### 1. Better Organization in GitHub UI
Workflows are now grouped by category:
```
Build - Docker Image
Deploy - Wiki
PR - Lint Commit Messages
PR - Test Councils
PR - Validate HACS
PR - Validate Release Ready
Release - Bump Version
Release - Publish to PyPI
Release - Rollback
Scheduled - Test All Councils
CodeQL
```

### 2. Clear Purpose
The name immediately tells you:
- **When** it runs (PR, Release, Scheduled)
- **What** it does (Test, Validate, Build, Deploy)

### 3. Easy Filtering
You can quickly find all workflows in a category:
- All PR checks: Look for "PR -"
- All release workflows: Look for "Release -"
- All scheduled jobs: Look for "Scheduled -"

### 4. Consistent Documentation
Documentation can reference workflows by their clear, descriptive names.

## Workflow Execution Order

### On Pull Request:
1. **PR - Lint Commit Messages** - Validates commit format
2. **PR - Test Councils** - Tests changed scrapers
3. **PR - Validate Release Ready** - Validates configuration
4. **PR - Validate HACS** - Validates HA integration

### On Merge to Master:
1. **Release - Bump Version** - Creates version bump and tag
2. **Release - Publish to PyPI** - Publishes to PyPI (triggered by tag)
3. **Deploy - Wiki** - Updates wiki (if wiki files changed)
4. **Build - Docker Image** - Builds Docker images

### On Schedule:
1. **Scheduled - Test All Councils** - Nightly full test run

### Manual Triggers:
1. **Release - Rollback** - Emergency rollback of bad release

## Adding New Workflows

When adding new workflows, follow the naming pattern:

### Choose a Category:
- **PR -** For pull request validation
- **Release -** For release-related tasks
- **Scheduled -** For scheduled jobs
- **Build -** For building artifacts
- **Deploy -** For deploying/publishing
- **Security -** For security scanning

### Choose a Clear Action:
- Use active verbs: Test, Validate, Build, Deploy, Publish
- Be specific: "Test Councils" not just "Test"
- Keep it concise: 2-4 words after the category

### Examples:
- ✅ `PR - Validate Dependencies`
- ✅ `Release - Create Changelog`
- ✅ `Build - API Server`
- ✅ `Deploy - Documentation`
- ❌ `Test` (too vague)
- ❌ `PR - This workflow tests the councils` (too long)

## Updating Documentation

When referencing workflows in documentation, use the full name:

**Good:**
> The **Release - Bump Version** workflow automatically creates version tags.

**Avoid:**
> The bump workflow creates tags.

This makes documentation clearer and easier to search.

## Migration Notes

### Old Names → New Names

| Old Name | New Name | Change |
|----------|----------|--------|
| Bump Version | Release - Bump Version | Added category |
| Publish Release | Release - Publish to PyPI | Added category, clarified action |
| Rollback Release | Release - Rollback | Added category |
| Validate Release Ready | PR - Validate Release Ready | Added category |
| Lint Commit Message | PR - Lint Commit Messages | Added category, pluralized |
| Test Councils (Pull Request Only) | PR - Test Councils | Simplified, added category |
| Test Councils (Nightly Full Run) | Scheduled - Test All Councils | Clarified, added category |
| Validate with hassfest | PR - Validate HACS | Clarified, added category |
| Docker Image CI | Build - Docker Image | Simplified, added category |
| Deploy Wiki | Deploy - Wiki | Added category |
| CodeQL | CodeQL | No change (already clear) |

## Summary

✅ All workflows now follow consistent naming
✅ Easy to find and understand workflows
✅ Better organization in GitHub UI
✅ Clear documentation references
✅ Scalable pattern for future workflows

The naming convention makes your CI/CD pipeline more professional and maintainable! 🎯
