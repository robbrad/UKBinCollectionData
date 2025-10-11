# Release Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PULL REQUEST STAGE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

    Developer creates PR → master
            ↓
    ┌───────────────────────────────────────────────────────────┐
    │  Automated Checks Run in Parallel:                        │
    │                                                            │
    │  ✓ behave_pull_request.yml                               │
    │    - Unit tests (Python 3.12)                            │
    │    - Integration tests (changed councils only)           │
    │    - Parity check (councils/input.json/features)         │
    │                                                            │
    │  ✓ lint.yml                                              │
    │    - Validate conventional commit messages               │
    │                                                            │
    │  ✓ validate-release-ready.yml                            │
    │    - Check version file consistency                      │
    │    - Validate pyproject.toml                             │
    │    - Verify commitizen config                            │
    │                                                            │
    │  ✓ hacs_validation.yml                                   │
    │    - Validate Home Assistant integration                 │
    │                                                            │
    │  ✓ codeql-analysis.yml                                   │
    │    - Security scanning                                   │
    └───────────────────────────────────────────────────────────┘
            ↓
    All checks pass? → YES → Ready to merge
            ↓ NO
    Fix issues and push updates


┌─────────────────────────────────────────────────────────────────────────────┐
│                         MERGE TO MASTER STAGE                                │
└─────────────────────────────────────────────────────────────────────────────┘

    PR merged to master
            ↓
    ┌───────────────────────────────────────────────────────────┐
    │  bump.yml workflow triggers                               │
    │                                                            │
    │  1. Commitizen analyzes commits since last tag           │
    │     - feat: → minor bump (0.152.0 → 0.153.0)            │
    │     - fix: → patch bump (0.152.0 → 0.152.1)             │
    │     - BREAKING CHANGE → major bump (0.152.0 → 1.0.0)    │
    │                                                            │
    │  2. Updates version in:                                  │
    │     - pyproject.toml                                     │
    │     - manifest.json                                      │
    │     - const.py                                           │
    │                                                            │
    │  3. Creates commit: "bump: version X.Y.Z"                │
    │                                                            │
    │  4. Creates git tag: X.Y.Z                               │
    │                                                            │
    │  5. Pushes commit and tag to master                      │
    └───────────────────────────────────────────────────────────┘
            ↓
    Tag pushed → Triggers release workflow


┌─────────────────────────────────────────────────────────────────────────────┐
│                           RELEASE STAGE                                      │
└─────────────────────────────────────────────────────────────────────────────┘

    Tag X.Y.Z pushed
            ↓
    ┌───────────────────────────────────────────────────────────┐
    │  release.yml workflow triggers                            │
    │                                                            │
    │  1. Checkout tagged commit                               │
    │                                                            │
    │  2. Install Poetry and dependencies                      │
    │                                                            │
    │  3. Verify version matches tag                           │
    │     (Poetry version == Git tag)                          │
    │                                                            │
    │  4. Build Python package                                 │
    │     poetry build → creates dist/*.whl and dist/*.tar.gz  │
    │                                                            │
    │  5. Create GitHub Release                                │
    │     - Auto-generated release notes                       │
    │     - Attach build artifacts                             │
    │                                                            │
    │  6. Publish to PyPI                                      │
    │     poetry publish → uploads to pypi.org                 │
    └───────────────────────────────────────────────────────────┘
            ↓
    ┌───────────────────────────────────────────────────────────┐
    │  Release Complete! ✓                                      │
    │                                                            │
    │  - GitHub Release: github.com/robbrad/.../releases       │
    │  - PyPI Package: pypi.org/project/uk-bin-collection      │
    │  - HACS Update: Available to Home Assistant users        │
    └───────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMMIT MESSAGE EXAMPLES                              │
└─────────────────────────────────────────────────────────────────────────────┘

feat(councils): add Birmingham City Council support
→ Minor version bump (0.152.0 → 0.153.0)

fix(selenium): handle connection timeout errors
→ Patch version bump (0.152.0 → 0.152.1)

feat(api)!: change date format to ISO 8601

BREAKING CHANGE: API responses now use ISO 8601 dates
→ Major version bump (0.152.0 → 1.0.0)

docs: update README with new council instructions
→ No version bump (documentation only)


┌─────────────────────────────────────────────────────────────────────────────┐
│                         TROUBLESHOOTING FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Issue: Version bump didn't happen
    ↓
Check: Are commits using conventional format?
    ↓ NO → Fix commit messages and force push
    ↓ YES
Check: Is PERSONAL_ACCESS_TOKEN set?
    ↓ NO → Add secret in repo settings
    ↓ YES
Check: Bump workflow logs for errors
    ↓
Manual fix: Run commitizen locally

─────────────────────────────────────────────

Issue: Release didn't publish
    ↓
Check: Was tag created by bump workflow?
    ↓ NO → Check bump workflow logs
    ↓ YES
Check: Is PYPI_API_KEY valid?
    ↓ NO → Update secret in repo settings
    ↓ YES
Check: Release workflow logs for errors
    ↓
Manual fix: Run poetry publish locally


┌─────────────────────────────────────────────────────────────────────────────┐
│                         WORKFLOW DEPENDENCIES                                │
└─────────────────────────────────────────────────────────────────────────────┘

Secrets Required:
├── PERSONAL_ACCESS_TOKEN (for bump workflow)
│   └── Needs: repo write access
│
├── PYPI_API_KEY (for release workflow)
│   └── Needs: PyPI project upload permissions
│
└── CODECOV_TOKEN (for test coverage)
    └── Needs: Codecov project access

Environments:
├── bump (requires approval)
└── release (requires approval)

Configuration Files:
├── pyproject.toml
│   ├── [tool.poetry] version
│   └── [tool.commitizen] config
│
├── custom_components/uk_bin_collection/manifest.json
│   └── version field
│
└── custom_components/uk_bin_collection/const.py
    └── INPUT_JSON_URL (includes version)
```
