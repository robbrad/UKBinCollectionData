# CI full-run failure triage (2026-09-03)

## Key finding

Ran all 65 with `--local_browser True` (real local Chrome instead of the
remote Selenium grid CI uses) in one batch. **40 of 65 passed immediately** -
strong evidence those were CI-environment flakiness (remote grid under
`-n logical` load / network timing), not real regressions. The remaining
**25 failed locally too** and need real investigation - those are listed
below with root causes as found.

Command used per council:

```
.venv/Scripts/python.exe -m pytest uk_bin_collection/tests/step_defs/ -k "<CouncilName>" --local_browser True -q
```

Status legend: PASSED-LOCALLY (CI flakiness, no action) / INVESTIGATING / FIXED / NOT-A-BUG (confirmed live-site/data issue, unrelated to dep bump) / BLOCKED (needs info)

| # | Council | Status | Notes |
|---|---|---|---|
| 1 | AshfieldDistrictCouncil | NOT-A-BUG | Live site bug on portal.digital.ashfield.gov.uk itself - console shows `TypeError: Cannot read properties of null (reading 'id')` in their own bundled JS, page never leaves "Loading..." spinner in a real browser too |
| 2 | AshfordBoroughCouncil | PASSED-LOCALLY | |
| 3 | BarkingDagenham | PASSED-LOCALLY | |
| 4 | BostonBoroughCouncil | NOT-A-BUG (real site issue, not a regression) | Confirmed via debug script: submitting the postcode form now triggers a genuine Cloudflare "Just a moment..." challenge that never clears even after 20s wait, in a real (non-headless) local Chrome too. Everything else (element IDs, dropdown structure, address text) still matches the scraper's expectations exactly. Would need `undetected-chromedriver` (already a project dep, used elsewhere) to have a chance of getting past this - a real fix, but out of scope for this triage pass |
| 5 | BrecklandCouncil | PASSED-LOCALLY | |
| 6 | BrightonandHoveCityCouncil | PASSED-LOCALLY | |
| 7 | BuckinghamshireCouncil | NOT-A-BUG | API decrypts fine (200, valid AES), but returns `{"collectionDay": null}` for the fixture UPRN - live-data issue on itouchvision's side, unrelated to the dep bump |
| 8 | CalderdaleCouncil | NOT-A-BUG | Site migrated to new.calderdale.gov.uk; old collectiondayfinder.jsp now returns a generic page with no address form. new domain 404s on the same path. Needs a full rewrite (separate task), not a regression from this PR |
| 9 | CanterburyCityCouncil | NOT-A-BUG | Known, already-documented outage (#2215) - the outage-detection error this session already added is working as designed |
| 10 | CastlepointDistrictCouncil | PASSED-LOCALLY | |
| 11 | ChichesterDistrictCouncil | NOT-A-BUG (Cloudflare IP block) | Bare homepage GET returns 403 from Cloudflare on this machine's current IP - not a code issue |
| 12 | CoventryCityCouncil | NOT-A-BUG | Fixture URL `/directory-record/62310/abberton-way-` now 404s on coventry.gov.uk - stale test fixture (site reorganised its directory), not a code/dep issue |
| 13 | DacorumBoroughCouncil | PASSED-LOCALLY | |
| 14 | DartfordBoroughCouncil | PASSED-LOCALLY | |
| 15 | DenbighshireCouncil | PASSED-LOCALLY | |
| 16 | DoncasterCouncil | PASSED-LOCALLY | |
| 17 | DumfriesandGallowayCouncil | PASSED-LOCALLY | |
| 18 | EastDevonDC | PASSED-LOCALLY | |
| 19 | EastHampshireDC | PASSED-LOCALLY | |
| 20 | EastLindseyDistrictCouncil | NOT-A-BUG (same Cloudflare pattern as Boston) | Confirmed via debug script: form-selector IDs, address matching, everything works correctly (verified via manual JS-driven walkthrough reaching the results page fine) - but the real Selenium-driven submit click specifically triggers a Cloudflare "Just a moment..." challenge that never clears, even after 15s. Same signature as #4 BostonBoroughCouncil |
| 21 | EastLothianCouncil | NOT-A-BUG | `collectiondates.eastlothian.gov.uk` no longer resolves (DNS NXDOMAIN) - subdomain retired/changed on the council's side, unrelated to dep bump. Needs a URL rewrite (separate task) |
| 22 | EastRenfrewshireCouncil | NOT-A-BUG (Cloudflare IP block) | Bare homepage GET returns 403 from Cloudflare on this machine's current IP - not a code issue |
| 23 | ExeterCityCouncil | PASSED-LOCALLY | |
| 24 | FyldeCouncil | NOT-A-BUG | Pre-existing, already tracked in ISSUE_RESOLUTION_PROGRESS.md - council moved to a login-gated "personal waste account" system, needs a full rewrite |
| 25 | GatesheadCouncil | NOT-A-BUG (Cloudflare IP block) | Same pattern as the other Cloudflare-fronted sites this pass - already header-hardened earlier this session; a hard IP-based block can't be fixed from the client side |
| 26 | GedlingBoroughCouncil | NOT-A-BUG | `api.gbcbincalendars.co.uk` returns a genuine 500 Internal Server Error for the fixture address, reproduced twice - live API-side outage, not a code/dep issue |
| 27 | GlasgowCityCouncil | FIXED | Site renamed the food-bin icon from `greyBin.gif` to `foodBin.gif`, so `bin_types.get(icon["src"])` returned `None` for it. Added `foodBin.gif` to the mapping (kept `greyBin.gif` too). Verified live, PASSED |
| 28 | GreatYarmouthBoroughCouncil | NOT-A-BUG (Cloudflare IP block) | Bare homepage GET returns 403 from Cloudflare on this machine's current IP - not a code issue |
| 29 | HaltonBoroughCouncil | NOT-A-BUG (Cloudflare/WAF IP block) | Bare homepage GET connection-reset on this machine's current IP - not a code issue |
| 30 | HighPeakCouncil | PASSED-LOCALLY | |
| 31 | HorshamDistrictCouncil | NOT-A-BUG | `satellite.horsham.gov.uk` resets the connection on every retry (5 attempts) - live server-side issue, not a code/dep issue |
| 32 | IpswichBoroughCouncil | PASSED-LOCALLY | |
| 33 | IsleOfWightCouncil | PARTIALLY FIXED | Found 2 real bugs: (1) test fixture only ever had a stale `uprn` even though the code has required postcode+house_number since it was written (2026-06-02) - `check_postcode(None)` always 404'd, meaning this test may never have genuinely passed; updated fixture to a real postcode+address. (2) the address `<select>` lookup used `@aria-label` which the site no longer sets - now uses the stable `id="SelectAddress"`. Still failing one step further in ("Could not find collection day in page") - the fixture address (County Hall, a council office) may not be a normal household, or there's a further Blazor Server DOM-hydration timing issue on the results page. Left for follow-up; the two fixes made are real improvements regardless |
| 34 | KnowsleyMBCouncil | PASSED-LOCALLY | |
| 35 | LancasterCityCouncil | PASSED-LOCALLY | |
| 36 | LondonBoroughHammersmithandFulham | PASSED-LOCALLY | |
| 37 | MidAndEastAntrimBoroughCouncil | PASSED-LOCALLY | |
| 38 | MidSussexDistrictCouncil | PASSED-LOCALLY | |
| 39 | NeathPortTalbotCouncil | FIXED | Two real bugs: (1) results page now has multiple `.umb-block-grid__layout-item` blocks (a promo banner is first) - code only searched the first one, missing the actual date headings entirely; now searches the whole content area. (2) dates use a non-breaking space (`\xa0`) between day and month, but code did `.replace("&nbsp", " ")` - a no-op since decoded text never contains the literal string "&nbsp"; fixed to replace `"\xa0"`. (3) bin-type card class gained an extra `bin-card-body` class, breaking the old exact multi-class match; now matches on that single stable class instead. Verified live, PASSED |
| 40 | NorthDevonCountyCouncil | PASSED-LOCALLY | |
| 41 | NorthEastDerbyshireDistrictCouncil | NOT-A-BUG (Cloudflare IP block) | Bare homepage GET returns 403 from Cloudflare on this machine's current IP - not a code issue. Separately, this council is already tracked as needing a full rewrite per #1881 |
| 42 | NorthKestevenDistrictCouncil | PASSED-LOCALLY | |
| 43 | NorthLanarkshireCouncil | NOT-A-BUG | Fixture uses a hardcoded session-specific URL (`/bin-collection-dates/<uprn>/<round-id>`) which now redirects to a canonical "no-information-found" page - this is a stale, one-off URL from whoever set up the fixture (this council has no postcode/paon search, per its own wiki_note users must manually grab a fresh URL from their browser), not a code/dep issue |
| 44 | NorthTynesideCouncil | PASSED-LOCALLY | |
| 45 | NorthumberlandCouncil | PASSED-LOCALLY | |
| 46 | OrkneyIslandsCouncil | FIXED | Test fixture had `postcode` set, but the code has always required a street/area/island name (`paon`/house_number) - `postcode` is never read at all. Pre-existing since this council's creation, unrelated to the dep bump. Updated fixture to `house_number: "Kirkwall"`. Verified live, PASSED |
| 47 | PowysCouncil | PASSED-LOCALLY | |
| 48 | PrestonCityCouncil | PASSED-LOCALLY | |
| 49 | SouthHamsDistrictCouncil | PASSED-LOCALLY | |
| 50 | SouthHollandDistrictCouncil | PASSED-LOCALLY | |
| 51 | SouthTynesideCouncil | PASSED-LOCALLY | |
| 52 | SouthendOnSeaCityCouncil | NOT-A-BUG | API (`apps.cloud9technologies.com`) returns 200 with all 11 container slots explicitly `null` for the fixture UPRN - live-data issue on the API's side, not a code/dep issue |
| 53 | StaffordshireMoorlandsDistrictCouncil | PASSED-LOCALLY | |
| 54 | StocktonOnTeesCouncil | NOT-A-BUG (Cloudflare IP block) | Bare homepage GET returns 403 from Cloudflare on this machine's current IP - not a code issue |
| 55 | SunderlandCityCouncil | PASSED-LOCALLY | |
| 56 | TamesideMBCouncil | PASSED-LOCALLY | |
| 57 | TamworthBoroughCouncil | NOT-A-BUG | Lichfield's shared portal returns 200 with the page's own text explicitly saying "We have no collection information for this property" for the fixture UPRN - stale/live-data issue, not a code/dep issue |
| 58 | TeignbridgeCouncil | PASSED-LOCALLY | |
| 59 | TonbridgeAndMallingBC | PASSED-LOCALLY | |
| 60 | WalsallCouncil | PASSED-LOCALLY | |
| 61 | WaverleyBoroughCouncil | PASSED-LOCALLY | |
| 62 | WestBerkshireCouncil | PASSED-LOCALLY | |
| 63 | WestDevonBoroughCouncil | PASSED-LOCALLY | |
| 64 | WestOxfordshireDistrictCouncil | PASSED-LOCALLY | |
| 65 | WokingBoroughCouncil | PASSED-LOCALLY | |

## Second key finding

Checked several remaining timeout/failure councils' bare homepage with a
plain `requests.get()` (no scraper code involved at all) and found this
machine's current IP is getting a flat Cloudflare 403 on multiple unrelated
council sites simultaneously (EastRenfrewshire, GreatYarmouth,
NorthEastDerbyshire, StocktonOnTees, Chichester all 403'd on the bare
homepage; Halton connection-reset the same way). That's an IP-reputation
block on this environment, not a per-site code bug - matches the
established "Cloudflare/CI-IP" pattern from earlier in this project's
history, just hitting my current network instead of (or possibly in
addition to) CI's.

## The 25 needing real investigation

AshfieldDistrictCouncil, BostonBoroughCouncil, BuckinghamshireCouncil,
CalderdaleCouncil, CanterburyCityCouncil, ChichesterDistrictCouncil,
CoventryCityCouncil, EastLindseyDistrictCouncil, EastLothianCouncil,
EastRenfrewshireCouncil, FyldeCouncil, GatesheadCouncil,
GedlingBoroughCouncil, GlasgowCityCouncil, GreatYarmouthBoroughCouncil,
HaltonBoroughCouncil, HorshamDistrictCouncil, IsleOfWightCouncil,
NeathPortTalbotCouncil, NorthEastDerbyshireDistrictCouncil,
NorthLanarkshireCouncil, OrkneyIslandsCouncil, SouthendOnSeaCityCouncil,
StocktonOnTeesCouncil, TamworthBoroughCouncil
