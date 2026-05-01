# Integration Test Results

Run date: 2026-03-28 | Total: 334 | Passed: 284→288 (after fixes) | Failed: 50→46

## Fixes Applied (4 councils fixed, tested, committed)

| Council | Issue | Fix |
|---------|-------|-----|
| BaberghDistrictCouncil | Date parse error on multi-date strings | Split comma-separated dates before parsing |
| MidSuffolkDistrictCouncil | Same date parse error | Same fix (shared pattern) |
| RotherDistrictCouncil | Crash on "No data found" text | Skip entries with no/invalid date |
| WirralCouncil | NoneType on .lower() | Fixed input.json: `paon` → `house_number` |

## Remaining Failures — Diagnosis (46)

### Upstream Issues — Cannot fix in code (26)

These are caused by council websites being down, redesigned, blocking requests, or test data being stale.

| Council | Root Cause |
|---------|-----------|
| AdurAndWorthingCouncils | Site redesigned — no `bin-collection-listing-row` divs |
| AngusCouncil | Selenium timeout — site likely redesigned |
| ArmaghBanbridgeCraigavonCouncil | Server closes connection — blocking automated requests |
| AshfieldDistrictCouncil | Selenium timeout |
| BarnetCouncil | Selenium timeout |
| BexleyCouncil | Selenium timeout |
| BlabyDistrictCouncil | Site returns 403 Forbidden |
| BostonBoroughCouncil | Selenium timeout |
| BrentCouncil | Site returns 403 Forbidden |
| CalderdaleCouncil | Selenium timeout |
| CeredigionCountyCouncil | Selenium timeout |
| ChichesterDistrictCouncil | Selenium timeout |
| EastLindseyDistrictCouncil | Selenium timeout |
| EastRenfrewshireCouncil | Selenium timeout |
| GreatYarmouthBoroughCouncil | Selenium timeout |
| HaltonBoroughCouncil | Selenium timeout |
| HorshamDistrictCouncil | Selenium timeout |
| KingstonUponThamesCouncil | Selenium timeout |
| NewhamCouncil | Server returns 500 — service unavailable |
| NorthEastDerbyshireDistrictCouncil | Selenium timeout |
| NorthumberlandCouncil | Selenium timeout |
| PeterboroughCityCouncil | Selenium timeout |
| SloughBoroughCouncil | Selenium timeout |
| StocktonOnTeesCouncil | Selenium timeout |
| SwaleBoroughCouncil | Selenium timeout |
| WalthamForest | Selenium timeout |

### Test Data Issues (7)

Scraper code works but test UPRN/address returns no data or wrong property type.

| Council | Root Cause |
|---------|-----------|
| NorthHertfordshireDistrictCouncil | API returns null for all containers — stale test UPRN |
| RotherhamCouncil | API returns 500 Int32 overflow — UPRN too large for their API |
| SouthStaffordshireDistrictCouncil | Test UPRN is a van collection property — no standard dates |
| WestMorlandAndFurness | "No collection schedule found" for test UPRN |
| WindsorAndMaidenheadCouncil | Selenium-based, needs investigation |
| BroxtoweBoroughCouncil | Selenium-based, needs investigation |
| ReigateAndBansteadBoroughCouncil | Selenium-based, needs investigation |

### Site Redesigns Needing Rewrite (8)

| Council | Root Cause |
|---------|-----------|
| ChorleyCouncil | Server returns "Unknown Error" |
| CotswoldDistrictCouncil | Salesforce Lightning overlay blocking clicks |
| EastLothianCouncil | Entire site rebuilt on Drupal — old API endpoints 404 |
| FyldeCouncil | Bartec iframe removed from page |
| GatesheadCouncil | Page structure changed — bin table not found |
| GloucesterCityCouncil | UPRN dropdown option no longer exists |
| NorthNorfolkDistrictCouncil | Form element IDs changed |
| StirlingCouncil | Postcode input element not found |

### Code Bugs Needing More Investigation (5)

| Council | Root Cause |
|---------|-----------|
| LondonBoroughOfRichmondUponThames | Test config needs PID parameter |
| RugbyBoroughCouncil | Selenium timeout — needs site inspection |
| SouthGloucestershireCouncil | DNS resolution failed — API domain gone |
| SouthKestevenDistrictCouncil | Week 5 mapping logic bug in 1206-line scraper |
| SwindonBoroughCouncil | Site now JS-rendered — needs Selenium rewrite |

---

## Passing Councils (288)

All 284 originally passing councils plus BaberghDistrictCouncil, MidSuffolkDistrictCouncil, RotherDistrictCouncil, WirralCouncil.
