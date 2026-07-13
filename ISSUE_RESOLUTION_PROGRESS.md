# Issue Resolution Progress

## Next Issue: continue nightly-suite triage (Halton/Mid & East Antrim/West Oxfordshire genuine
Selenium timeouts, or #1560 Gateshead - now have a local Selenium grid)

## July 2026 Release: [PR #2154](https://github.com/robbrad/UKBinCollectionData/pull/2154) (merged) + [PR #2155](https://github.com/robbrad/UKBinCollectionData/pull/2155) (follow-up)

20 open community/dependabot PRs consolidated onto `july-release-26`, plus 29 additional
issues/bugs fixed while validating the branch and triaging a full nightly integration
run. All fixes verified live (pure HTTP directly, Selenium-based ones against a local
Docker Selenium grid, or undetected-chromedriver against a local Chrome for
Cloudflare-gated sites). Issues below are commented with a link to the PR and are wired
up (`fixes #NNNN` in the PR body) to auto-close when the PR is merged to master.

**Note:** #2154 was merged as a regular (non-squash) merge from a snapshot of
`july-release-26` that predated the last 5 fixes below (Mid Suffolk, Wiltshire,
Pembrokeshire retry, Rochford, HA sensor availability) - those are carried to
`master` by the follow-up [PR #2155](https://github.com/robbrad/UKBinCollectionData/pull/2155)
instead.

### ⚠️ Breaking change: automations keyed on the bin sensor's `unavailable` state

The HA sensor availability fix (#1672, in PR #2155) changes when the **main bin
sensor** (`sensor.<name>_<bin_type>`) reports `unavailable`, for **every council**,
not just the ones it was filed against - this is generic integration code, not
council-specific.
- **Before:** went `unavailable` whenever that bin type had no upcoming date in the
  current data (e.g. a seasonal service currently out of season) - indistinguishable
  from a real fetch failure.
- **After:** only goes `unavailable` when the coordinator update itself genuinely
  fails. No date for a bin type now shows the state `"No collections scheduled"`
  and stays available.
- **Action needed:** any automation triggering on this sensor's state being
  `unavailable` to detect "this bin type isn't in service right now" must be
  updated to check for `"No collections scheduled"` instead once #2155 merges.
  Automations reacting to `unavailable` to catch a genuine integration failure are
  unaffected and should be more reliable than before.

### Other side effects worth knowing about

- **Shared HTTP fetch retry** (#2073 fix, PR #2155): affects **101 of the 352**
  councils in `input.json` (the ones using the default `requests`-based fetch path -
  149 handle their own requests via `skip_get_url`, 102 use Selenium, neither
  affected). Adds resilience against transient errors, but a genuinely-down council
  site now takes longer to fail (up to ~46s of retry backoff alone, on top of each
  attempt's own connection time) instead of failing immediately - and may surface
  as a generic HA "Timeout while updating data" instead of a more specific
  connection error, since the retries can outlast HA's own per-update timeout.
- **Lewes/Eastbourne DB-outage detection** (#2127 fix, PR #2157): during a future
  EnvironmentFirst outage, sensors for these two councils will now go `unavailable`
  with a clear log message instead of silently continuing to show the last known
  good (stale) collection dates. Scoped to just these two councils.
- **Removing the unused `ocr` extra** (PR #2156): no functional change for any
  council (nothing used it); only affects anyone with `pip install
  uk_bin_collection[ocr]` pinned externally.

## Issues Fixed This Session: 24 (16 direct fixes + 8 covered by merged PRs)

| Issue | Council | Status | Notes |
|-------|---------|--------|-------|
| #2125 | Stratford-on-Avon | Fixed | UPRN-only configs now skip the postcode lookup entirely |
| #2126 | Fenland | Fixed | API needs its own small PremiseID, not a national UPRN; test fixture was also wrong |
| #2149 | High Peak | Fixed | Rewritten for the new Syncfusion "Public Dashboard" |
| #2120 | Powys | Fixed | Cookie-consent dialog was intercepting the Find address click |
| #1945 | Bolsover | Fixed | WeekBlack/WeekBandG are "1"/"2" (alternating week), not booleans - Round B was silently dropped |
| #2146 | Newcastle | Fixed | Rewritten for the ReCollect widget API (old AJAX endpoint retired) |
| #2150 | Torridge | Fixed | Same webservice, now reached via the council's AchieveForms broker instead of the retired SOAP endpoint |
| #2141 | Ceredigion | Fixed | "Every 3 weeks" panel used a different auto-generated class than the hardcoded one |
| #2140 | Sunderland | Fixed | Cloudflare-gated; rewritten with undetected-chromedriver (new dependency) - needs local Chrome, not remote grid; see CI note below |
| #2139 | Staffordshire Moorlands | Fixed | Same Syncfusion Public Dashboard migration as High Peak (#2149) |
| #2111 | Bedford | Fixed | API dropped the trailing `/{days}` path segment; now also returns past jobs, added a date filter |
| #2109 | Mid Suffolk | Fixed | Postcode field lost its `aria-label`; results moved from cards to a `<table>`. Rewritten to target stable ids and parse the new table |
| #2098 | Wiltshire | Fixed | `select_one()` only captured the first same-day event; iterate all `.rc-event-container` elements per day |
| #2073 | Pembrokeshire | Fixed | Shared HTTP fetch had no retry, so a transient `ConnectionResetError` failed the whole update; wired in `build_retry_session()` |
| #1462 | Rochford | Fixed | Use end of the published collection-week range, not the start, so "next collection" isn't skipped a fortnight early |
| #1672 | (garden waste) | Fixed | Main bin sensor's `available` now keys off `coordinator.last_update_success` like every other sensor; shows "No collections scheduled" instead of Unavailable when a type has no upcoming date |
| #2147 | Rugby | Fixed | Merged via #2148 |
| #2136 | Wigan | Fixed | Merged via #2145 (supersedes #2131) |
| #2114 | Warrington | Fixed | Merged via #2134 |
| #2117 | East Cambridgeshire | Fixed | Merged via #2132 |
| #2116 | Vale of White Horse | Fixed | Merged via #2115 |
| #1907 | South Kesteven | Fixed | Merged via #2121 full rewrite (supersedes #2119) |
| #1670 | South Kesteven | Fixed | Merged via #2121 |
| #1668 | South Kesteven | Fixed | Merged via #2121 |
| #2000 | South Kesteven | Fixed | Merged via #2121 |

Also fixed while validating merged PRs or triaging the nightly suite (no separate issue
filed):
- **BirminghamCityCouncil** - `NameError: date_format` crash left by PR #2144
- **EdenDistrictCouncil** - own portal stopped showing bin days; now delegates to WestMorlandAndFurness's working backend (same UPRNs, Eden was absorbed into that unitary authority)
- **DarlingtonBoroughCouncil** - results page lost its `#detailsDisplay` wrapper and moved the date out of an `<h3>` into a plain `<p class="bold">`
- **WaverleyBoroughCouncil** - one-character bug: `soup.find_all("u1", ...)` (numeral) instead of `"ul"` (the tag), so the results block was always empty
- **SomersetCouncil** - two bugs: date lookup used `soup.find()` against the whole page instead of the current bin's own block, and crashed outright when a bin type had no second "followed by" date

**CI note (Sunderland):** the GitHub Actions integration-test workflow runs councils
against a remote `selenium/standalone-chrome` grid service. Sunderland's new
undetected-chromedriver-based scraper can't use that - it needs a real local Chrome +
display (e.g. Xvfb). It will fail in the current CI harness until that's addressed;
this is a maintainer decision, not made in this session.

## Investigated, not fixed

| Issue | Council | Notes |
|-------|---------|-------|
| #2113 | Haringey | New site is behind AWS WAF Bot Control (CloudFront), not Cloudflare. Plain Selenium blocked; undetected-chromedriver also blocked (5/5 attempts). A pure-HTTP rewrite isn't feasible either - the site is a Next.js app using server actions, not a discoverable REST API. Needs a more specialized bypass (e.g. residential-IP browser farm) or a different data source. Findings posted on the issue. |
| #1884 | Ealing | Re-verified live: the previously-reported bug (`collectionDateString` vs `collectionDate`) is already fixed in both `EalingCouncil.py` and `LondonBoroughEaling.py` (commit 57c8b1a9); both return correct data today. Only the module-duplication cleanup remains, deliberately deferred (deleting/merging either would break existing users' saved config). |
| #1881 | NE Derbyshire | Re-checked live: self-service form still redirects to the homepage, only PDF calendars available, no postcode/address lookup exists. No change since the last update on the issue. Holding off on a PDF+area-list rewrite per earlier guidance - large, fragile, and possibly throwaway if the council republishes the form. |

## Code Fixes Made

| Commit | Council | Fix |
|--------|---------|-----|
| 0fd90006 | StratfordUponAvonCouncil | Skip postcode lookup entirely when UPRN already known |
| 5d1b4a86 | BirminghamCityCouncil | Import missing `date_format` from common |
| ac15aa21 | FenlandDistrictCouncil | Accept PremiseID directly via uprn param; fixed test fixture |
| 6e9033a5 | HighPeakCouncil | Rewrite for new Syncfusion Public Dashboard |
| 3fee3223 | PowysCouncil | Dismiss cookie consent prompt before Find address click |
| e26b8310 | BolsoverCouncil | Correctly handle Round B (WeekBlack/WeekBandG == "2") |
| c3ed3a5a | NewcastleCityCouncil | Rewrite for ReCollect API |
| 34aa0faf | TorridgeDistrictCouncil | Reach getRoundCalendarForUPRN via AchieveForms broker |
| f629330f | CeredigionCountyCouncil | Capture all schedule panels, not just "Weekly" |
| 22390ee6 | SunderlandCityCouncil | Bypass Cloudflare with undetected-chromedriver |
| 1bef35c1 | EdenDistrictCouncil | Delegate to WestMorlandAndFurness backend |
| 0a5856e6 | StaffordshireMoorlandsDistrictCouncil | Rewrite for new Syncfusion Public Dashboard |
| 534aefe5 | DarlingtonBoroughCouncil | Update selectors for redesigned results page |
| f766bc2f | WaverleyBoroughCouncil | Fix `"u1"` tag-name typo, should be `"ul"` |
| b37921d9 | BedfordBoroughCouncil | Drop stale `/35` path segment, filter past dates |
| 7c13317e | SomersetCouncil | Scope date lookups per-bin, handle missing "followed by" date |
| e60ccc54 | MidSuffolkDistrictCouncil | Rewrite selectors for redesigned postcode form; parse new results table |
| 7e028b4b | WiltshireCouncil | Capture all same-day event containers, not just the first |
| 3d61f3d6 | get_bin_data.py (shared) | Use build_retry_session() for the default HTTP fetch |
| d3af17bd | RochfordCouncil | Use end of collection-week range; harden mojibake separator parsing |
| 16df19e8 | custom_components/sensor.py | Base bin sensor availability on coordinator.last_update_success |
| 65261e47 | LincolnCouncil | Fix NoneType error when UPRN not provided (zfill on None) [prior session] |

## Nightly integration suite triage

Ran the full `uk_bin_collection/tests/step_defs/` suite (~352 councils) against a local
Docker Selenium grid: **66 failed, 286 passed**. Triaged all 66:

**Confirmed environmental noise (not real bugs), ~35 councils:**
- ~21 `SessionNotCreatedException` failures were pure Selenium-grid contention - a
  single-node `selenium/standalone-chrome` container can only run one session at a
  time, and the full suite runs many xdist workers in parallel. Re-running the same
  councils sequentially (`-n 1`) passed almost all of them.
- 7 `NameResolutionError`/DNS failures (Aberdeen, Bristol, Buckinghamshire, Brent,
  Braintree, Amber Valley, Dover) were transient - all resolved fine on retry via curl.
- `ambervalley.gov.uk` "SSL" failure was a local CA trust store gap in raw curl, not a
  real site issue (the scraper itself already disables cert verification).

**Fixed, see above:** Staffordshire Moorlands, Bedford, Eden, Darlington, Waverley,
Somerset.

**Confirmed stale test fixtures, not code bugs (need a fresh valid UPRN):**
- SouthendOnSeaCityCouncil - API returns `null` for every container for this UPRN
- TamworthBoroughCouncil (Lichfield portal) - "We have no collection information for this property"
- WalsallCouncil - API 504 Gateway Timeout at time of testing (their server, not us)
- NorthWestLeicestershire, OrkneyIslandsCouncil - test fixtures missing required disambiguation params (house_number / area name)

**Confirmed genuine remaining bugs, not yet fixed (24 councils):**
HaltonBoroughCouncil, MidAndEastAntrimBoroughCouncil, WestOxfordshireDistrictCouncil
(genuine Selenium timeouts, confirmed real via sequential re-run), GlasgowCityCouncil
(`AttributeError`), FyldeCouncil ("Unexpected response"), HackneyCouncil
(`JSONDecodeError`), EastDevonDC (403 Forbidden), IsleOfWightCouncil /
NewarkAndSherwoodDC ("Invalid postcode Status: 404" - same symptom, worth checking
together), Hillingdon (`StaleElementReferenceException`), SwaleBoroughCouncil, EastLindseyDistrictCouncil,
AngusCouncil, AshfieldDistrictCouncil (Selenium `TimeoutException`), BarkingDagenham
(`ElementNotInteractableException`), GedlingBoroughCouncil, IslingtonCouncil
(`ReadTimeout` - possibly transient, worth a retry),
HorshamDistrictCouncil (connection reset), SouthKestevenDistrictCouncil (hit a live
"business rule 4143" error on the council's own site, same as seen earlier in this
session - likely transient), NorthEastDerbyshireDistrictCouncil (matches open issue
#1881, needs full rewrite), NewhamCouncil (timed out during triage, not yet
investigated), BelfastCityCouncil (page now shows a "must enable JavaScript" fallback
for a plain-`requests` POST - needs investigation into whether a hidden anti-bot field
is missing or a genuine Selenium rewrite is needed), DartfordBoroughCouncil (not yet
investigated), ForestOfDeanDistrictCouncil (Selenium, empty bins, not yet investigated).

## Remaining Issues (not covered above)

| Issue | Council | Type | Notes |
|-------|---------|------|-------|
| #2153 | Lincoln | Bug (no repro) | Works fine with known-good test UPRN; asked reporter for error/UPRN/postcode |
| #2127 | Lewes/Eastbourne/Seaford | Info only | Reporter already diagnosed as upstream DB outage, not a code bug |
| #2118 | Flintshire | Enhancement | Add Brown/Garden waste entity |
| #2079 | Slough | Bug (Selenium timeout) | Cookie banner element never appears in headless mode |
| #1986 | Mid Suffolk | Enhancement | Expose additional future collection dates |
| #1784 | Selenium Addon Removed | HA ecosystem | Not a code bug - HA's Selenium add-on repo was removed; needs a docs/wiki note about running `selenium/standalone-chrome` via Docker instead |
| #1560 | Gateshead | Bug (wrong dates) | Now have a local Selenium grid available - worth revisiting next session |
