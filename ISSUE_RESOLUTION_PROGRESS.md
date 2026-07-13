# Issue Resolution Progress

## Next Issue: continue nightly-suite triage (Halton/Mid & East Antrim/West Oxfordshire genuine
Selenium timeouts, or #1560 Gateshead - now have a local Selenium grid)

## July 2026 Release: [PR #2154](https://github.com/robbrad/UKBinCollectionData/pull/2154)

20 open community/dependabot PRs consolidated onto `july-release-26`, plus 25 additional
issues/bugs fixed while validating the branch and triaging a full nightly integration
run. All fixes verified live (pure HTTP directly, Selenium-based ones against a local
Docker Selenium grid, or undetected-chromedriver against a local Chrome for
Cloudflare-gated sites). Issues below are commented with a link to the PR and are wired
up (`fixes #NNNN` in the PR body) to auto-close when the PR is merged to master.

## Issues Fixed This Session: 20 (12 direct fixes + 8 covered by merged PRs)

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

**Confirmed genuine remaining bugs, not yet fixed (25 councils):**
HaltonBoroughCouncil, MidAndEastAntrimBoroughCouncil, WestOxfordshireDistrictCouncil
(genuine Selenium timeouts, confirmed real via sequential re-run), GlasgowCityCouncil
(`AttributeError`), FyldeCouncil ("Unexpected response"), HackneyCouncil
(`JSONDecodeError`), EastDevonDC (403 Forbidden), IsleOfWightCouncil /
NewarkAndSherwoodDC ("Invalid postcode Status: 404" - same symptom, worth checking
together), Hillingdon (`StaleElementReferenceException`), SwaleBoroughCouncil, EastLindseyDistrictCouncil,
AngusCouncil, AshfieldDistrictCouncil (Selenium `TimeoutException`), BarkingDagenham
(`ElementNotInteractableException`), GedlingBoroughCouncil, IslingtonCouncil
(`ReadTimeout` - possibly transient, worth a retry), PembrokeshireCountyCouncil,
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
| #2098 | Wiltshire | Bug (logic) | Alternating fortnightly bins showing only 1 of 2 same-day bins |
| #2079 | Slough | Bug (Selenium timeout) | Cookie banner element never appears in headless mode |
| #2073 | Pembrokeshire | Bug (session expiry) | Data goes unavailable every ~12hrs, needs HA-side investigation |
| #1986 | Mid Suffolk | Enhancement | Expose additional future collection dates |
| #1884 | Ealing | Cleanup | Two modules (EalingCouncil/LondonBoroughEaling) for the same council; removing either would break existing users' saved config, needs a deprecation plan not just a delete |
| #1881 | NE Derbyshire | Bug (form removed) | Confirmed failing in nightly suite too; needs full rewrite |
| #1784 | Selenium Addon Removed | HA ecosystem | Not a code bug - HA's Selenium add-on repo was removed; needs a docs/wiki note about running `selenium/standalone-chrome` via Docker instead |
| #1672 | (garden waste) | Enhancement | Show "No Collections Scheduled" instead of Unavailable |
| #1560 | Gateshead | Bug (wrong dates) | Now have a local Selenium grid available - worth revisiting next session |
| #1462 | Rochford | Enhancement (week offset) | Low priority |
