# Issue Resolution Progress

## Next Issue: nightly integration suite triage (in progress) or #1560 (Gateshead - now have a local Selenium grid)

## July 2026 Release: [PR #2154](https://github.com/robbrad/UKBinCollectionData/pull/2154)

20 open community/dependabot PRs consolidated onto `july-release-26`, plus 10 additional
issues fixed while validating the branch. All fixes verified live (pure HTTP directly,
Selenium-based ones against a local Docker Selenium grid, or undetected-chromedriver
against a local Chrome for Cloudflare-gated sites). Issues below are commented with a
link to the PR and are wired up (`fixes #NNNN` in the PR body) to auto-close when the
PR is merged to master.

## Issues Fixed This Session: 18 (10 direct fixes + 8 covered by merged PRs)

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
| #2147 | Rugby | Fixed | Merged via #2148 |
| #2136 | Wigan | Fixed | Merged via #2145 (supersedes #2131) |
| #2114 | Warrington | Fixed | Merged via #2134 |
| #2117 | East Cambridgeshire | Fixed | Merged via #2132 |
| #2116 | Vale of White Horse | Fixed | Merged via #2115 |
| #1907 | South Kesteven | Fixed | Merged via #2121 full rewrite (supersedes #2119) |
| #1670 | South Kesteven | Fixed | Merged via #2121 |
| #1668 | South Kesteven | Fixed | Merged via #2121 |
| #2000 | South Kesteven | Fixed | Merged via #2121 |

Also fixed while validating merged PRs (no separate issue): a `NameError: date_format`
crash left in BirminghamCityCouncil by PR #2144.

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
| 65261e47 | LincolnCouncil | Fix NoneType error when UPRN not provided (zfill on None) [prior session] |

## Remaining Issues

| Issue | Council | Type | Notes |
|-------|---------|------|-------|
| #2153 | Lincoln | Bug (no repro) | Works fine with known-good test UPRN; asked reporter for error/UPRN/postcode |
| #2139 | Staffordshire Moorlands | Bug (no repro) | Report cuts off with no URL or specifics; asked reporter for detail |
| #2127 | Lewes/Eastbourne/Seaford | Info only | Reporter already diagnosed as upstream DB outage, not a code bug |
| #2118 | Flintshire | Enhancement | Add Brown/Garden waste entity |
| #2111 | Bedford | Bug (no repro) | Only an attached log file; asked reporter to paste the actual error text |
| #2109 | Mid Suffolk | Bug | Selenium stacktrace crash, needs live investigation |
| #2098 | Wiltshire | Bug (logic) | Alternating fortnightly bins showing only 1 of 2 same-day bins |
| #2079 | Slough | Bug (Selenium timeout) | Cookie banner element never appears in headless mode |
| #2073 | Pembrokeshire | Bug (session expiry) | Data goes unavailable every ~12hrs, needs HA-side investigation |
| #1986 | Mid Suffolk | Enhancement | Expose additional future collection dates |
| #1884 | Ealing | Cleanup | Two modules (EalingCouncil/LondonBoroughEaling) for the same council; removing either would break existing users' saved config, needs a deprecation plan not just a delete |
| #1881 | NE Derbyshire | Bug (form removed) | Self-service lookup form fully removed by council, needs full rewrite |
| #1784 | Selenium Addon Removed | HA ecosystem | Not a code bug - HA's Selenium add-on repo was removed; needs a docs/wiki note about running `selenium/standalone-chrome` via Docker instead |
| #1672 | (garden waste) | Enhancement | Show "No Collections Scheduled" instead of Unavailable |
| #1560 | Gateshead | Bug (wrong dates) | Now have a local Selenium grid available - worth revisiting next session |
| #1462 | Rochford | Enhancement (week offset) | Low priority |

## Nightly integration suite

Full `uk_bin_collection/tests/step_defs/` run in progress against all ~350 councils
using a local Docker Selenium grid. Results to be triaged in the next update to this
file.
