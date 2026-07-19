# South Kesteven and Home Assistant hardening candidate

> **Candidate status:** This document describes an experimental branch in the
> `Dozi3/UKBinCollectionData` fork, based on upstream `0.170.6`
> (`36d920520e4a4c64fb6278557d357b948bf95e88`). It is not an official
> UKBinCollectionData release, has not been merged into
> `robbrad/UKBinCollectionData`, and does not indicate upstream acceptance.

## Purpose

This branch addresses the South Kesteven District Council (SKDC) scraper and
the Home Assistant integration path that runs it.

The reported Home Assistant failure happened before the SKDC scraper itself
executed. Selenium imported the `websocket` top-level package, but Python found
a misplaced `/config/websocket/__init__.py` ahead of the installed
`websocket-client` distribution. That file was an internal Home Assistant
custom-integration module and attempted a parent-relative import while loaded
as a top-level package:

```text
ImportError: attempted relative import beyond top-level package
```

The candidate makes this class of dependency collision diagnosable and
prevents it from appearing as an unexplained, repeatedly retried coordinator
failure.

## What changed

### Core package and import isolation

- Councils are resolved from validated, fully qualified package names.
- Selenium imports are deferred until a browser-backed council actually needs
  them. Non-Selenium councils therefore do not import the browser stack merely
  because the package is loaded.
- Before WebDriver creation, the candidate validates that the imported
  `websocket` module belongs to the installed `websocket-client` distribution.
- Dependency shadowing, missing optional dependencies, browser
  unavailability, address mismatches, upstream denials, and council-site drift
  have distinct typed errors.
- Household identifiers and identifier-bearing URLs are redacted from normal
  logs. Diagnostic screenshots and HTML are opt-in.
- Shared Selenium type annotations no longer force runtime browser imports.

Many council files changed only to defer Selenium imports and redact exception
text. Those mechanical changes are intended to preserve each council's
existing scraper behavior while preventing a browser dependency problem from
breaking unrelated councils.

Across the candidate, 122 council adapters are touched and 83 of them move
Selenium imports out of module scope. The branch adds 155 test functions. This
is deliberately a broad import-isolation change, so package-wide deterministic
validation remains a publication gate even though SKDC is the only council
exercised live.

- USRN and browser user-agent values now propagate through the supported CLI
  and Home Assistant paths.
- WebDriver URLs and remote-command settings are validated before use.
- Partially created browser sessions are cleaned up when startup fails.
- Birmingham no longer relies on an undeclared `yarl` dependency.

### South Kesteven District Council

- The standalone `requests.get()` preflight was removed. That preflight could
  receive an environment-dependent HTTP 403 even when a real browser session
  was permitted to use the service.
- One bounded Selenium session begins at the public `/binday` page and follows
  the supported self-service checker in the same browser context.
- Property selection uses exact normalized house-number or house-name
  matching. Missing and ambiguous matches fail explicitly instead of silently
  choosing the first address.
- Page, element, and total-run timeouts are bounded.
- Page and element operations are bounded to 30 seconds, the SKDC run has a
  90-second deadline, and Home Assistant provides a 125-second outer boundary
  so browser cleanup can complete.
- WebDriver cleanup runs in `finally`, including error and timeout paths.
- Browser HTTP 403 responses, selector/form drift, address mismatch, and
  WebDriver failure remain distinguishable in Home Assistant diagnostics.

### Home Assistant integration

- Config-entry arguments use an explicit typed mapping. Boolean options such
  as `skip_get_url`, headless mode, and local-browser mode are emitted as
  flags rather than `--flag=True`.
- Postcode, house number/name, URL, WebDriver endpoint, user agent, timeout,
  and supported flags are carried end to end into the selected council.
- Config entries use schema version 4 with sequential migration and
  normalization of historical field aliases.
- Old SKDC entries missing a postcode, house number/name, or WebDriver
  endpoint require reconfiguration rather than guessed values.
- Initial setup, options, and reconfiguration use the same council metadata
  and validation rules.
- Dependency, browser, and configuration failures can create actionable Home
  Assistant Repairs instead of repeated generic tracebacks.
- Refreshes are serialized per entry, stale-data behavior is explicit, and
  the calendar platform no longer performs a duplicate initial scrape.
- Existing collection payloads and sensor/calendar entity identity contracts
  are retained.

### Release and workflow safeguards

- Release validation checks the core-wheel/component contract.
- Release ordering requires the matching core artifact before the integration
  manifest can expose it.
- Deterministic tests are separated from live canaries.
- GitHub Actions used by the changed workflows are pinned immutably.
- Workflow tests cover release ordering, manifest pinning, and rollback
  contracts.

## Commit series

The runtime candidate tested on Home Assistant is
`9139a7a0bf8199e0755fce0946f3d8f0b97c7940`. It contains these commits after
upstream `0.170.6`:

| Commit | Purpose |
| --- | --- |
| `183afcbe` | Harden SKDC, shared imports, logging, Home Assistant setup, migrations, diagnostics, and release gates |
| `edb88701` | Align deterministic validation with the exact Home Assistant target |
| `4a862602` | Validate rootless capability drops dynamically |
| `99b00fba` | Remove Birmingham's undeclared URL dependency |
| `d33c6476` | Support Selenium status and session-cleanup validation |
| `790577a9` | Isolate disposable-runner imports |
| `d148e7f7` | Honor Home Assistant Repair persistence timing |
| `7c43de91` | Preserve the complete migration/entity contract |
| `241d7425` | Validate unstarted-canary network intent |
| `da704563` | Bind the Podman canary to the inspected command only |
| `9139a7a0` | Isolate the project test package from installed dependencies |

The branch-level documentation commit is intentionally separate from the
runtime candidate so the tested code identity remains clear.

## Validation evidence

### Deterministic validation

Before the live trial, the exact runtime commit completed the focused
core/SKDC deterministic selection on all supported Python generations:

| Runtime | Result |
| --- | ---: |
| Python 3.12 | 145 passed |
| Python 3.13 | 145 passed |
| Python 3.14 | 145 passed |

These focused results validate the changed import, SKDC, and core behavior.
They are not a claim that every council website was contacted successfully.
Fresh fork CI is required for the complete deterministic matrix before this
candidate is considered ready for an upstream pull request or release.

### Reproducible live-trial artifact

The runtime commit was exported from Git rather than from the dirty working
tree. A unique prerelease wheel was built twice and produced byte-identical
output:

| Item | Value |
| --- | --- |
| Trial version | `0.170.6rc2026071901` |
| Wheel SHA-256 | `7D8B15AC3016F2856AFEEB09DA1A2B6A3323853953CB62AB983F808CF0838B61` |
| Staged manifest SHA-256 | `5B188CD6BA8353D92692F8D113B396F67A97BA386CC9B30932FC60105EF99C3D` |
| Wheel tag | `py3-none-any` |
| Python declaration | `>=3.12,<3.15` |

The generated trial manifest differed from the committed public manifest only
in `version` and `requirements`. It used a local, SHA-256-pinned direct wheel
reference; that generated manifest is not committed to this branch.

### User-authorized live Home Assistant trial

On 19 July 2026, the exact wheel and component were installed in a controlled,
reversible trial on the user's actual Home Assistant host:

| Component | Observed runtime |
| --- | --- |
| Home Assistant Core | `2026.7.2` |
| Python | `3.14` |
| Home Assistant OS | `18.1` |
| Selenium | `4.46.0`, ARM64 |
| WebDriver route | Remote endpoint ending in `/wd/hub` |

The live result was:

- the configuration wizard loaded the hash-pinned local wheel successfully;
- one real SKDC lookup completed using the repository's public test fixture;
- Home Assistant created 10 UK Bin Collection devices and 36 entities;
- sensor values and next-collection dates were populated;
- calendar entities were created;
- no displayed UK Bin Collection entity was unavailable or unknown;
- `attempted relative import beyond top-level package` did not recur;
- no UK Bin Collection unexpected-error entry appeared in the post-run Core
  log;
- the genuine HACS integration remained available;
- the WebDriver returned to ready state with zero active sessions; and
- the live wheel and component hashes still matched the staged artifacts.

No other council was exercised live on that Home Assistant host. Confidence in
other councils comes from deterministic tests and import isolation, not from a
claim that every council's external website was manually tested.

## Known limitations and publication gates

### This branch is not yet a self-contained HACS release

The committed component remains version `0.170.6` and requests:

```text
uk-bin-collection>=0.170.6
```

The already published PyPI `0.170.6` wheel is not this hardened candidate.
Installing this branch directly through HACS would therefore not guarantee
that Home Assistant installs the hardened core package used in the successful
live trial.

A durable release must:

1. assign a new, unique core-package version;
2. publish the exact reviewed core wheel;
3. verify that artifact and its supported Python range;
4. update the custom-component manifest to the exact matching version; and
5. publish the component and core artifact atomically.

Until that happens, this branch is for source review and controlled testing
only. It must not be tagged, published as a GitHub Release, or described as a
normal HACS installation.

### Remaining gates

- Run the full deterministic Python 3.12/3.13/3.14 workflow on this fork
  branch.
- Run HACS/HassFest validation on the pushed branch.
- Re-run the exact Home Assistant compatibility matrix for any runtime code
  change after `9139a7a0`.
- Synchronize the new form, validation, and Repair strings into the
  non-English translation files. Home Assistant can fall back to English, but
  the missing Welsh, Irish, Scottish Gaelic, and Portuguese entries are not
  upstream-release quality.
- Review CI results before requesting any upstream pull request.
- Obtain separate approval before contacting or submitting anything to the
  upstream repository.

Broader networking/TLS centralization, collection-event modeling, supplier
adapter consolidation, and council-registry caching are outside this focused
candidate.

## Rollback and support status

This candidate was trialed only after a full Home Assistant backup and a
verified off-host copy were created. Manual trials should follow the same
practice and preserve a reversible copy of any conflicting path before it is
moved.

The fork branch is not an upstream-supported release. Official support and
release expectations remain with the upstream project unless and until the
changes are accepted there.
