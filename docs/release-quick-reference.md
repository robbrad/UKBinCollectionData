# Release Workflow Quick Reference

## Commit Message Cheat Sheet

| Type | Version Bump | Example |
|------|--------------|---------|
| `feat:` | Minor (0.152.0 → 0.153.0) | `feat(councils): add Leeds support` |
| `fix:` | Patch (0.152.0 → 0.152.1) | `fix(selenium): handle timeout` |
| `feat!:` or `BREAKING CHANGE:` | Major (0.152.0 → 1.0.0) | `feat!: change API format` |
| `docs:` | None | `docs: update README` |
| `style:` | None | `style: format code` |
| `refactor:` | None | `refactor: simplify parser` |
| `test:` | None | `test: add unit tests` |
| `chore:` | None | `chore: update dependencies` |

## Workflow Stages

```
PR → Tests → Merge → Bump (auto) → Tag (auto) → Release (auto) → PyPI (auto)
```

Everything after merge is fully automated!

## How It Works

1. **Developer**: Create PR with conventional commits
2. **CI**: Validates commits and runs tests
3. **Merge**: PR merged to master
4. **Commitizen**: Analyzes commits, bumps version, updates CHANGELOG
5. **Git**: Creates tag and pushes
6. **Release**: Publishes to PyPI and GitHub

## Common Commands

```bash
# Check current version
poetry version -s

# Validate before PR
make pre-build

# Run tests locally
make unit-tests
make integration-tests

# Check commit messages
git log --oneline

# Manual bump (if needed)
cz bump --yes --changelog
git push origin master --follow-tags
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Version bump didn't happen | Check commit message format (must use `feat:` or `fix:`) |
| Release didn't trigger | Check if tag was created in bump workflow logs |
| PyPI publish failed | Verify `PYPI_API_KEY` secret is set |
| Permission error | Verify `APP_ID` and `APP_PRIVATE_KEY` secrets are set |
| Version files out of sync | Commitizen handles this automatically |

## Required Secrets

- `APP_ID` - GitHub App ID (for protected branches)
- `APP_PRIVATE_KEY` - GitHub App private key
- `PYPI_API_KEY` - For PyPI publishing
- `CODECOV_TOKEN` - For test coverage (optional)

**Note:** Uses GitHub App for secure, non-expiring authentication

## Workflow Files

- `behave_pull_request.yml` - PR tests
- `lint.yml` - Commit message validation
- `validate-release-ready.yml` - Pre-merge checks
- `bump.yml` - Automated version bumping and tagging
- `release.yml` - Publishing to PyPI and GitHub

## Version Files (Auto-Synced)

Commitizen automatically updates:
- `pyproject.toml`
- `custom_components/uk_bin_collection/manifest.json`
- `custom_components/uk_bin_collection/const.py`
- `CHANGELOG.md`

## Quick Links

- [Full Documentation](./release-workflow.md)
- [Setup Checklist](./release-workflow-setup-checklist.md)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Commitizen](https://commitizen-tools.github.io/commitizen/)
