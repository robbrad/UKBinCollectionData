# Issue Resolution Progress

## Next Issue: FyldeCouncil needs a full rewrite for its new login-gated "personal
waste account" system (if feasible without real user credentials), or GedlingBoroughCouncil's
upstream API needs re-checking for stability

## Deep-dive triage round 2 (2026-07-13, PR #2165)

Worked through every council flagged as "genuinely broken, needs individual
investigation" from the previous triage pass, plus Gateshead (#1560) and re-checks
on a couple of previously-confirmed-broken ones.

**6 real fixes:**
- **EastLindseyDistrictCouncil**: form element ids are year-versioned
  (`WASTECOLLECTIONDAYS202526`); the council rolled to `202627`. Matched on the
  stable id suffix instead of hardcoding a year, so this won't break again at the
  next rollover.
- **AngusCouncil**: AchieveForms form rebuilt - `searchString`→`search`,
  `customerAddress`→`select_NewAddress`, plus a new required "Show Calendar" button
  click. Results markup unchanged.
- **BarkingDagenham**: a promotional overlay (`.prefix-overlay`) sits on top of the
  page and intercepts clicks/typing on everything below it, including the cookie
  banner - `ElementNotInteractableException` on the postcode field. Now dismisses
  both overlays explicitly.
- **MidAndEastAntrimBoroughCouncil**: the embedded iframe widget is gone entirely -
  moved to a linked-out WhiteSpace WRP portal (same platform as 8 other councils
  already in this repo, e.g. WaverleyBoroughCouncil). Rewrote as pure HTTP, no
  Selenium needed. **Breaking change**: now takes postcode + house number as
  separate parameters instead of the whole address crammed into postcode (a quirk
  of the old iframe's free-text search that no longer applies).
- **SwaleBoroughCouncil**: not a Cloudflare block - the old fallback message was a
  guess, not a diagnosis (verified the page loads completely normally). The Squiz
  Matrix form was rebuilt with new field ids; results page structure unchanged.
- **DartfordBoroughCouncil**: the site silently serves a stripped-down page with no
  results table for requests without a browser-like User-Agent - the scraper sent
  none, always got the empty variant, and silently returned zero bins instead of
  erroring. Sent the project's UA string and made a missing table a hard error.
  This was never actually a dead backend, as the earlier triage pass (using a
  UA-less request) concluded - worth remembering when re-checking "confirmed dead
  backend" verdicts, since a missing User-Agent can look identical to a genuine
  outage.

**Hardening only, live issue not resolved:**
- **HorshamDistrictCouncil**: switched to `build_retry_session()` for consistency,
  but verified live it still fails after 5 retries - a sustained connection reset,
  not a transient blip.
- **GatesheadCouncil** (#1560): removed a stray unconditional debug file write
  (`debug_page.html` to cwd on every run) and a stale error message referencing it.
  Could not reproduce the reported "stuck date" symptom live - scraper currently
  produces correctly advancing dates. Commented on the issue asking for more detail.

**Confirmed not fixable here:**
- **HaltonBoroughCouncil**: genuine Google reCAPTCHA v2 - confirmed blocked even
  with `undetected-chromedriver` against a real local, non-headless Chrome. Same
  class of problem as Haringey (#2113).
- **AshfieldDistrictCouncil**: a genuine client-side JS error on the council's own
  portal (`Cannot read properties of null (reading 'id')`) leaves the page stuck on
  "Loading..." for every visitor, not just automation.
- **GedlingBoroughCouncil**: re-checked, still unstable (3 different failures across
  3 live attempts this pass too).
- **FyldeCouncil**: re-checked, still on the login-gated "personal waste account"
  system with no public lookup.

**Systematic audit completed (2026-07-13, same PR #2165):** followed up on the
Aberdeenshire "page-ignoring" risk class rather than leaving it as noted latent
risk. Re-ran the AST scan (fixed a bug in the first pass - it missed councils that
reassign `page = requests.get(...)` immediately, which discards the framework's
fetch just as completely as never referencing `page` at all) and found **79**
councils with the same shape, not 59. Spot-checked a sample and confirmed the
overwhelming majority are a single shared AchieveForms/apibroker template
(`SESSION_URL` + `API_URL`, e.g. Bolsover, Dudley, Aberdeen City) that never needed
the framework's fetch. Marked all 79 `skip_get_url: true`, closing off the
regression risk class entirely. Verified via a full live BDD run of all 79 (had to
route around an unrelated pytest-xdist worker-crash flake under parallel execution
by using a plain Python driver script calling `pytest.main()` directly instead of
the `-k "A or B or ..."` shell expression, which also turned out to be silently
truncating itself under Windows Git Bash) - 78 passed, 1 failed (FyldeCouncil, the
same pre-existing unrelated failure documented above).

## Post-#2154-merge full-suite triage (2026-07-13)

Reconfigured the local Docker Selenium grid for real concurrency (was capped at
`SE_NODE_MAX_SESSIONS=1`, causing most of the earlier "66 failed" run to be pure
session-contention noise) - recreated with `SE_NODE_MAX_SESSIONS=8`,
`SE_NODE_OVERRIDE_MAX_SESSIONS=true`, `--shm-size 4g` (host has 32 CPU/32GB available
to Docker). Ran the full 352-council suite at `-n 8` (matched to the grid's real
capacity, not `-n logical`/32 which would just recreate the contention problem): **26
failed, 326 passed in 5m21s** - a much cleaner signal than the previous run.

**Found and fixed a self-inflicted regression** from the #2073 retry fix (shipped in
0.168.0): `AberdeenshireCouncil`'s `parse_data()` ignores the page it's given and
makes its own request to a working endpoint, but the generic framework fetch to an
*unused* root URL ran first regardless - that URL happens to return a persistent 500
on the council's own end, and the new retry logic correctly (if unfortunately) turned
that into a hard failure, breaking every user's sensors (reported live as #2158).
Fixed by overriding `get_data()` for that council to skip the pointless fetch - see
[PR #2159](https://github.com/robbrad/UKBinCollectionData/pull/2159). Found 59 other
councils with the same *shape* (page ignored, own request made, no `skip_get_url`)
via AST scan, but cross-referenced against real failures and only Aberdeenshire is
currently affected - the rest have `url` fields that happen to point somewhere
healthy. Worth a slower systematic audit sometime, not urgent.

Triage of the 26 failures:
- **2 transient** (CheltenhamBoroughCouncil, BoltonCouncil) - DNS failures during the
  run, hosts resolve fine on recheck.
- **4 stale test fixtures** - NorthWestLeicestershire/OrkneyIslandsCouncil (missing
  disambiguation params), SouthendOnSeaCityCouncil/TamworthBoroughCouncil (fixture
  UPRN has no live collections). Also newly found: **IsleOfWightCouncil and
  NewarkAndSherwoodDC's "Invalid postcode Status: 404"** turned out to be the same
  root cause - both fixtures are missing the required `postcode` field entirely
  (only `uprn` is set), so `check_postcode(None)` queries
  `api.postcodes.io/postcodes/None` and legitimately 404s. Not a scraper bug; needs
  a maintainer to supply a real postcode for the existing UPRN (couldn't resolve one
  via free public UPRN-lookup APIs).
- **3 fixed:**
  - AberdeenshireCouncil (#2158) - see above, [PR #2159](https://github.com/robbrad/UKBinCollectionData/pull/2159)
  - EastDevonDC - 403 was purely a missing User-Agent header (default
    `python-requests/x.x` UA gets blocked; the project's own polite scraper UA
    string works fine). [PR #2160](https://github.com/robbrad/UKBinCollectionData/pull/2160)
  - GlasgowCityCouncil, KnowsleyMBCouncil, Hillingdon - re-ran clean on retest
    (KnowsleyMBCouncil 3/3, GlasgowCityCouncil and Hillingdon both passed on a
    sequential re-run with no worker contention) - these were flakes from the old
    single-session grid, not real bugs. No code change needed.
- **1 hardened, not fixed:** HorshamDistrictCouncil - switched to
  `build_retry_session()` for consistency ([PR #2161](https://github.com/robbrad/UKBinCollectionData/pull/2161)),
  but verified live it still fails after 5 retries - a sustained block/outage on
  their end, not a transient blip. Live issue remains unfixed.
- **16 confirmed genuinely broken, not fixed this pass:**
  - **GedlingBoroughCouncil** - `api.gbcbincalendars.co.uk` is unstable right now:
    3 separate live attempts gave 3 different failures (500, 500, ReadTimeout).
    Not us; their backend.
  - **DartfordBoroughCouncil** - the scraper's endpoint
    (`windmz.dartford.gov.uk/ufs/...`) now 404s under a bare default IIS placeholder
    page - the whole legacy "Universal Form Service" subsystem looks decommissioned.
    The council's *own* current site still links to this dead endpoint, so there's
    no alternative URL to fall back to yet. Needs the council to actually publish a
    working replacement before this is fixable.
  - **FyldeCouncil** - the page no longer has the `bartec-iframe` the scraper looks
    for; the whole page has moved to a login-gated "personal waste account" system
    with no public UPRN-based lookup visible anymore. Likely needs a much bigger
    rework (if even feasible without real user credentials), not a quick selector
    fix.
  - **SwaleBoroughCouncil** - confirmed Cloudflare bot-check blocking page load
    (the scraper's own diagnostic print already says so). Same class of problem as
    Sunderland (#2140, fixed with undetected-chromedriver) / Haringey (#2113,
    still unfixed - AWS WAF, not Cloudflare). Not attempted this pass.
  - **EastLindseyDistrictCouncil, AngusCouncil, HaltonBoroughCouncil,
    AshfieldDistrictCouncil, BarkingDagenham, MidAndEastAntrimBoroughCouncil** -
    confirmed genuinely broken on a sequential re-run (not contention), each with a
    generic Selenium `TimeoutException` (or `ElementNotInteractableException` /
    `NoSuchFrameException`) - needs individual selector/page-change investigation
    per council, not done this pass given time already spent.
  - **HaringeyCouncil, NorthEastDerbyshireDistrictCouncil** - already deeply
    investigated earlier this session (see "Investigated, not fixed" below);
    unchanged.

## July 2026 Release: [PR #2154](https://github.com/robbrad/UKBinCollectionData/pull/2154) (merged) + [PR #2155](https://github.com/robbrad/UKBinCollectionData/pull/2155) (follow-up)

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
| 28627dc3 | AberdeenshireCouncil | Skip unused root-URL fetch that was breaking the whole scraper (#2158) |
| 29a242d0 | EastDevonDC | Send scraper User-Agent header to get past a 403 block |
| 7a5a585e | HorshamDistrictCouncil | Use build_retry_session() for resilience (hardening, not a fix) |
| 65261e47 | LincolnCouncil | Fix NoneType error when UPRN not provided (zfill on None) [prior session] |
| 82886007 | EalingCouncil / LondonBoroughEaling | Dedupe #1884 - see note below |

**Dedupe (Ealing, #1884):** both modules hit the same
`WasteCollectionWS/home/FindCollection` API and, per the maintainer's own earlier
comment on the issue, deleting either would break existing users' saved config (the
council module name is stored verbatim and dynamically imported - see
`collect_data.py`'s `import_council_module`). Picked `LondonBoroughEaling` as
canonical on the merits rather than by fiat: it matches this repo's own established
naming convention for London boroughs (10 other councils use the
`LondonBorough<Name>` pattern; `EalingCouncil` is the outlier), and its
implementation was slightly more complete (explicit JSON `Content-Type` + a real
`status_code` check, vs. `EalingCouncil.py`'s vestigial
`requests.packages.urllib3.disable_warnings()` call that had no effect since nothing
in that file ever passed `verify=False`). `EalingCouncil.py` is now a two-line shim
that delegates to `LondonBoroughEaling.CouncilClass` - same behaviour, zero
duplicated logic, still importable under its old name.

Also found and fixed a latent bug this surfaced: both `input.json` entries shared the
identical `wiki_name` ("Ealing"), and the Home Assistant config flow builds its
council dropdown from `wiki_name` then maps a selection back to a council key via
`list.index()` (`config_flow.py`'s `map_wiki_name_to_council_key`) - a linear search
that always resolves to whichever entry happens to come first, so new users picking
"Ealing" from the dropdown had no reliable way to choose between the two. Renamed
`EalingCouncil`'s `wiki_name` to `"Ealing (deprecated, use LondonBoroughEaling)"` so
it's distinguishable and existing users' saved selections are unaffected.

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
| #2118 | Flintshire | Enhancement | Scraper already correctly extracts "Brown Bin" when present (verified live) - likely an opt-in subscription question, not a code gap. Also found an unrelated minor bug: a schedule-note row (`*New Round* - Tuesday AHP`) gets parsed as if it were a bin type. Asked reporter to confirm subscription status. |
| #2079 | Slough | Bug (Selenium timeout) | Could not reproduce: exact production config succeeded 5/5 live runs, <1.1s each. The community-proposed fix's diagnosis (Cloudflare, zero window size) doesn't hold up - no Cloudflare signature in headers, and window-size is already hardcoded to 1920x1080 regardless of council code. Likely transient or reporter-environment-specific (e.g. cloud/CI IP). Commented asking reporter to confirm it's still happening. |
| #1986 | Mid Suffolk | Enhancement | Expose additional future collection dates |
| #1784 | Selenium Addon Removed | HA ecosystem | Not a code bug - HA's Selenium add-on repo was removed; needs a docs/wiki note about running `selenium/standalone-chrome` via Docker instead |
| #1560 | Gateshead | Bug (wrong dates) | Now have a local Selenium grid available - worth revisiting next session |
