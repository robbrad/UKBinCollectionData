# Integration Test Results

Run date: 2026-03-28 | Total: 334 | Passed: 284 (85%) | Failed: 50 (15%)

---

## Failed Councils — Detailed Diagnostics (50)

### Category: SELENIUM_TIMEOUT (22)

These councils use Selenium for browser automation and the expected page elements were not found within the timeout period. Likely causes: council redesigned their website, changed element IDs/classes, added cookie consent overlays, or the page structure changed.

| Council | Lines | URL | Fix Approach |
|---------|-------|-----|--------------|
| AngusCouncil | 164 | angus.gov.uk | Inspect page for changed selectors/form flow |
| AshfieldDistrictCouncil | 116 | ashfield.gov.uk | Inspect page for changed selectors |
| BarnetCouncil | 263 | barnet.gov.uk | Inspect page for changed selectors |
| BexleyCouncil | 128 | waste.bexley.gov.uk | Inspect page for changed selectors |
| BostonBoroughCouncil | 207 | boston.gov.uk | Inspect page for changed selectors |
| CalderdaleCouncil | 123 | calderdale.gov.uk | Inspect page for changed selectors |
| CeredigionCountyCouncil | 158 | ceredigion.gov.uk | Inspect page for changed selectors |
| ChichesterDistrictCouncil | 162 | chichester.gov.uk | Inspect page for changed selectors |
| EastLindseyDistrictCouncil | 107 | e-lindsey.gov.uk | Inspect page for changed selectors |
| EastRenfrewshireCouncil | 123 | eastrenfrewshire.gov.uk | Inspect page for changed selectors |
| GreatYarmouthBoroughCouncil | 151 | great-yarmouth.gov.uk | Inspect page for changed selectors |
| HaltonBoroughCouncil | 165 | halton.gov.uk | Inspect page for changed selectors |
| HorshamDistrictCouncil | 124 | horsham.gov.uk | Inspect page for changed selectors |
| KingstonUponThamesCouncil | 111 | waste-services.kingston.gov.uk | Inspect page for changed selectors |
| NorthEastDerbyshireDistrictCouncil | 126 | ne-derbyshire.gov.uk | Inspect page for changed selectors |
| NorthumberlandCouncil | 173 | bincollection.northumberland.gov.uk | Inspect page for changed selectors |
| PeterboroughCityCouncil | 168 | report.peterborough.gov.uk | Inspect page for changed selectors |
| RugbyBoroughCouncil | 147 | rugby.gov.uk | Inspect page for changed selectors |
| SloughBoroughCouncil | 159 | slough.gov.uk | Inspect page for changed selectors |
| StirlingCouncil | 164 | stirling.gov.uk | Postcode input element not found — page redesign |
| StocktonOnTeesCouncil | 160 | stockton.gov.uk | Inspect page for changed selectors |
| SwaleBoroughCouncil | 146 | swale.gov.uk | Inspect page for changed selectors |
| WalthamForest | 127 | portal.walthamforest.gov.uk | AchieveForms page likely changed |

### Category: EMPTY_BINS (11)

Scraper runs without error but returns zero bin entries. The page loads but the data extraction logic finds nothing — likely the HTML structure or API response format changed.

| Council | Selenium? | Lines | Fix Approach |
|---------|-----------|-------|--------------|
| BlabyDistrictCouncil | No | 64 | Check API response format changes |
| BrentCouncil | No | 130 | Check HTML/API response for changed structure |
| BroxtoweBoroughCouncil | Yes | 114 | Check page source after Selenium load |
| NewhamCouncil | No | 68 | Check API at bincollection.newham.gov.uk |
| ReigateAndBansteadBoroughCouncil | Yes | 82 | Check page source after Selenium load |
| RotherhamCouncil | No | 89 | Check HTML structure at rotherham.gov.uk |
| SouthStaffordshireDistrictCouncil | No | 110 | Check HTML at sstaffs.gov.uk |
| SwindonBoroughCouncil | No | 58 | Check API response format |
| WestMorlandAndFurness | No | 66 | Check API response format |
| WindsorAndMaidenheadCouncil | Yes | 66 | Check page source after Selenium load |

### Category: VALUE_ERROR (9)

Scraper hits a specific parsing/logic error. These are the most fixable — the error messages point directly to the bug.

| Council | Error | Fix Approach |
|---------|-------|--------------|
| AdurAndWorthingCouncils | No bin collection rows found in HTML | HTML table structure changed — update selectors |
| BaberghDistrictCouncil | unconverted data remains: `, Mon 27 Apr 2026` | Date format changed — council now returns multi-date strings, need to split before parsing |
| ChorleyCouncil | Final bin table not found. Server said: Unknown Error | Server-side error — may be transient or API endpoint changed |
| EastLothianCouncil | No streets found for postcode EH21 6QA | API response format changed or postcode lookup broken |
| GatesheadCouncil | Could not find bin collections table in page source | Page HTML structure changed |
| LondonBoroughOfRichmondUponThames | supply a URL with ?pid= OR put PID in House Number field | Test config missing required PID parameter in input.json |
| MidSuffolkDistrictCouncil | unconverted data remains: `, Tue 28 Apr 2026` | Same date parsing bug as BaberghDistrictCouncil (likely shared code) |
| NorthHertfordshireDistrictCouncil | No valid bin collection data from API | API response format changed |
| RotherDistrictCouncil | time data 'No data found' does not match format '%A %d %B' | API returning "No data found" text instead of date — needs error handling |
| SouthKestevenDistrictCouncil | No bin type found for 30/03/2026 (Week 5 of 3/2026) | Calendar week mapping logic broken — 1206-line scraper with complex week logic |

### Category: CONNECTION_ERROR (2)

Council server is unreachable or rejecting connections.

| Council | Error | Fix Approach |
|---------|-------|--------------|
| ArmaghBanbridgeCraigavonCouncil | Remote end closed connection without response | Server may be blocking automated requests or temporarily down — add retry/headers |
| SouthGloucestershireCouncil | DNS resolution failed for api.southglos.gov.uk | API domain no longer exists — need to find new endpoint |

### Category: ELEMENT_NOT_FOUND (2)

Selenium finds the page but a specific element is missing.

| Council | Error | Fix Approach |
|---------|-------|--------------|
| GloucesterCityCouncil | Cannot locate option with value: 100120479507 | UPRN dropdown option no longer exists — test data or form changed |
| NorthNorfolkDistrictCouncil | Unable to locate element `[id="F_Address_subform:Postcode"]` | Form element ID changed — update selector |

### Category: CLICK_INTERCEPTED (1)

Selenium finds the element but another element is blocking the click (overlay, cookie banner, etc).

| Council | Error | Fix Approach |
|---------|-------|--------------|
| CotswoldDistrictCouncil | Element click intercepted by `<flowruntime-lwc-body>` | Salesforce Lightning overlay blocking — need to wait for/dismiss overlay or use JS click |

### Category: ATTRIBUTE_ERROR (1)

Python code error — a None value where an object was expected.

| Council | Error | Fix Approach |
|---------|-------|--------------|
| WirralCouncil | 'NoneType' object has no attribute 'lower' | Scraper expects an element that no longer exists — add null check or update selector |

### Category: GENERAL_EXCEPTION (1)

| Council | Error | Fix Approach |
|---------|-------|--------------|
| FyldeCouncil | Unexpected response from fylde.gov.uk | API response format changed — inspect new response |

---

## Autonomous Fix Priority

Easiest to fix (code bugs, not site changes):
1. **BaberghDistrictCouncil + MidSuffolkDistrictCouncil** — Same date parsing bug, split on comma before parsing
2. **RotherDistrictCouncil** — Add "No data found" error handling before date parse
3. **SouthKestevenDistrictCouncil** — Week 5 mapping logic bug
4. **LondonBoroughOfRichmondUponThames** — Fix input.json test config (add PID)
5. **WirralCouncil** — Add null check before `.lower()` call

Medium difficulty (need to inspect current site):
6. **AdurAndWorthingCouncils** — HTML structure change, non-Selenium
7. **Empty bins councils** (11 councils) — Check API/HTML responses
8. **NorthNorfolkDistrictCouncil** — Update element ID selector
9. **GloucesterCityCouncil** — Update UPRN or form handling
10. **CotswoldDistrictCouncil** — Handle Salesforce overlay

Hardest (full Selenium timeout — site likely redesigned):
11. **22 Selenium timeout councils** — Each needs individual site inspection

---

## Passing Councils (284)

| # | Council |
|---|---------|
| 1 | AberdeenCityCouncil |
| 2 | AberdeenshireCouncil |
| 3 | AmberValleyBoroughCouncil |
| 4 | AntrimAndNewtonabbeyCouncil |
| 5 | ArdsAndNorthDownCouncil |
| 6 | ArgyllandButeCouncil |
| 7 | ArunCouncil |
| 8 | AshfordBoroughCouncil |
| 9 | BCPCouncil |
| 10 | BarkingDagenham |
| 11 | BarnsleyMBCouncil |
| 12 | BasildonCouncil |
| 13 | BasingstokeCouncil |
| 14 | BathAndNorthEastSomersetCouncil |
| 15 | BedfordBoroughCouncil |
| 16 | BedfordshireCouncil |
| 17 | BelfastCityCouncil |
| 18 | BirminghamCityCouncil |
| 19 | BlackburnCouncil |
| 20 | BlackpoolCouncil |
| 21 | BlaenauGwentCountyBoroughCouncil |
| 22 | BolsoverCouncil |
| 23 | BoltonCouncil |
| 24 | BracknellForestCouncil |
| 25 | BradfordMDC |
| 26 | BraintreeDistrictCouncil |
| 27 | BrecklandCouncil |
| 28 | BrightonandHoveCityCouncil |
| 29 | BristolCityCouncil |
| 30 | BroadlandDistrictCouncil |
| 31 | BromleyBoroughCouncil |
| 32 | BromsgroveDistrictCouncil |
| 33 | BroxbourneCouncil |
| 34 | BuckinghamshireCouncil |
| 35 | BurnleyBoroughCouncil |
| 36 | BuryCouncil |
| 37 | CambridgeCityCouncil |
| 38 | CannockChaseDistrictCouncil |
| 39 | CanterburyCityCouncil |
| 40 | CardiffCouncil |
| 41 | CarmarthenshireCountyCouncil |
| 42 | CastlepointDistrictCouncil |
| 43 | CharnwoodBoroughCouncil |
| 44 | ChelmsfordCityCouncil |
| 45 | CheltenhamBoroughCouncil |
| 46 | CherwellDistrictCouncil |
| 47 | CheshireEastCouncil |
| 48 | CheshireWestAndChesterCouncil |
| 49 | ChesterfieldBoroughCouncil |
| 50 | ColchesterCityCouncil |
| 51 | ConwyCountyBorough |
| 52 | CornwallCouncil |
| 53 | CoventryCityCouncil |
| 54 | CrawleyBoroughCouncil |
| 55 | CroydonCouncil |
| 56 | CumberlandCouncil |
| 57 | DacorumBoroughCouncil |
| 58 | DarlingtonBoroughCouncil |
| 59 | DartfordBoroughCouncil |
| 60 | DenbighshireCouncil |
| 61 | DerbyCityCouncil |
| 62 | DerbyshireDalesDistrictCouncil |
| 63 | DoncasterCouncil |
| 64 | DorsetCouncil |
| 65 | DoverDistrictCouncil |
| 66 | DudleyCouncil |
| 67 | DumfriesandGallowayCouncil |
| 68 | DundeeCityCouncil |
| 69 | DurhamCouncil |
| 70 | EalingCouncil |
| 71 | EastAyrshireCouncil |
| 72 | EastCambridgeshireCouncil |
| 73 | EastDevonDC |
| 74 | EastDunbartonshireCouncil |
| 75 | EastHertsCouncil |
| 76 | EastRidingCouncil |
| 77 | EastStaffordshireBoroughCouncil |
| 78 | EastSuffolkCouncil |
| 79 | EastbourneBoroughCouncil |
| 80 | EastleighBoroughCouncil |
| 81 | EdenDistrictCouncil |
| 82 | EdinburghCityCouncil |
| 83 | ElmbridgeBoroughCouncil |
| 84 | EnfieldCouncil |
| 85 | EnvironmentFirst |
| 86 | EppingForestDistrictCouncil |
| 87 | EpsomandEwellBoroughCouncil |
| 88 | ErewashBoroughCouncil |
| 89 | ExeterCityCouncil |
| 90 | FalkirkCouncil |
| 91 | FarehamBoroughCouncil |
| 92 | FenlandDistrictCouncil |
| 93 | FermanaghOmaghDistrictCouncil |
| 94 | FifeCouncil |
| 95 | FlintshireCountyCouncil |
| 96 | FolkestoneandHytheDistrictCouncil |
| 97 | ForestOfDeanDistrictCouncil |
| 98 | GedlingBoroughCouncil |
| 99 | GlasgowCityCouncil |
| 100 | GooglePublicCalendarCouncil |
| 101 | GosportBoroughCouncil |
| 102 | GraveshamBoroughCouncil |
| 103 | GuildfordCouncil |
| 104 | GwyneddCouncil |
| 105 | HackneyCouncil |
| 106 | HarboroughDistrictCouncil |
| 107 | HaringeyCouncil |
| 108 | HarlowCouncil |
| 109 | HarrogateBoroughCouncil |
| 110 | HartDistrictCouncil |
| 111 | HartlepoolBoroughCouncil |
| 112 | HastingsBoroughCouncil |
| 113 | HerefordshireCouncil |
| 114 | HertsmereBoroughCouncil |
| 115 | HighPeakCouncil |
| 116 | HighlandCouncil |
| 117 | Hillingdon |
| 118 | HinckleyandBosworthBoroughCouncil |
| 119 | HullCityCouncil |
| 120 | HuntingdonDistrictCouncil |
| 121 | HyndburnBoroughCouncil |
| 122 | IpswichBoroughCouncil |
| 123 | IsleOfAngleseyCouncil |
| 124 | IslingtonCouncil |
| 125 | KingsLynnandWestNorfolkBC |
| 126 | KirkleesCouncil |
| 127 | KnowsleyMBCouncil |
| 128 | LancasterCityCouncil |
| 129 | LeedsCityCouncil |
| 130 | LeicesterCityCouncil |
| 131 | LewesDistrictCouncil |
| 132 | LichfieldDistrictCouncil |
| 133 | LincolnCouncil |
| 134 | LisburnCastlereaghCityCouncil |
| 135 | LiverpoolCityCouncil |
| 136 | LondonBoroughCamdenCouncil |
| 137 | LondonBoroughEaling |
| 138 | LondonBoroughHammersmithandFulham |
| 139 | LondonBoroughHarrow |
| 140 | LondonBoroughHavering |
| 141 | LondonBoroughHounslow |
| 142 | LondonBoroughLambeth |
| 143 | LondonBoroughLewisham |
| 144 | LondonBoroughRedbridge |
| 145 | LondonBoroughSutton |
| 146 | LutonBoroughCouncil |
| 147 | MaidstoneBoroughCouncil |
| 148 | MaldonDistrictCouncil |
| 149 | MalvernHillsDC |
| 150 | ManchesterCityCouncil |
| 151 | MansfieldDistrictCouncil |
| 152 | MedwayCouncil |
| 153 | MeltonBoroughCouncil |
| 154 | MertonCouncil |
| 155 | MidAndEastAntrimBoroughCouncil |
| 156 | MidDevonCouncil |
| 157 | MidSussexDistrictCouncil |
| 158 | MidUlsterDistrictCouncil |
| 159 | MiddlesbroughCouncil |
| 160 | MidlothianCouncil |
| 161 | MiltonKeynesCityCouncil |
| 162 | MoleValleyDistrictCouncil |
| 163 | MonmouthshireCountyCouncil |
| 164 | MorayCouncil |
| 165 | NeathPortTalbotCouncil |
| 166 | NewForestCouncil |
| 167 | NewarkAndSherwoodDC |
| 168 | NewcastleCityCouncil |
| 169 | NewcastleUnderLymeCouncil |
| 170 | NewportCityCouncil |
| 171 | NorthAyrshireCouncil |
| 172 | NorthDevonCountyCouncil |
| 173 | NorthEastLincs |
| 174 | NorthKestevenDistrictCouncil |
| 175 | NorthLanarkshireCouncil |
| 176 | NorthLincolnshireCouncil |
| 177 | NorthNorthamptonshireCouncil |
| 178 | NorthSomersetCouncil |
| 179 | NorthTynesideCouncil |
| 180 | NorthWarwickshireBoroughCouncil |
| 181 | NorthWestLeicestershire |
| 182 | NorthYorkshire |
| 183 | NorwichCityCouncil |
| 184 | NottinghamCityCouncil |
| 185 | NuneatonBedworthBoroughCouncil |
| 186 | OadbyAndWigstonBoroughCouncil |
| 187 | OldhamCouncil |
| 188 | OxfordCityCouncil |
| 189 | PembrokeshireCountyCouncil |
| 190 | PerthAndKinrossCouncil |
| 191 | PlymouthCouncil |
| 192 | PortsmouthCityCouncil |
| 193 | PowysCouncil |
| 194 | PrestonCityCouncil |
| 195 | ReadingBoroughCouncil |
| 196 | RedcarandClevelandCouncil |
| 197 | RedditchBoroughCouncil |
| 198 | RenfrewshireCouncil |
| 199 | RhonddaCynonTaffCouncil |
| 200 | RochdaleCouncil |
| 201 | RochfordCouncil |
| 202 | RoyalBoroughofGreenwich |
| 203 | RunnymedeBoroughCouncil |
| 204 | RushcliffeBoroughCouncil |
| 205 | RushmoorCouncil |
| 206 | SalfordCityCouncil |
| 207 | SandwellBoroughCouncil |
| 208 | SeftonCouncil |
| 209 | SevenoaksDistrictCouncil |
| 210 | SheffieldCityCouncil |
| 211 | ShropshireCouncil |
| 212 | SolihullCouncil |
| 213 | SomersetCouncil |
| 214 | SouthAyrshireCouncil |
| 215 | SouthCambridgeshireCouncil |
| 216 | SouthDerbyshireDistrictCouncil |
| 217 | SouthHamsDistrictCouncil |
| 218 | SouthHollandDistrictCouncil |
| 219 | SouthLanarkshireCouncil |
| 220 | SouthNorfolkCouncil |
| 221 | SouthOxfordshireCouncil |
| 222 | SouthRibbleCouncil |
| 223 | SouthTynesideCouncil |
| 224 | SouthamptonCityCouncil |
| 225 | SouthwarkCouncil |
| 226 | SpelthorneBoroughCouncil |
| 227 | StAlbansCityAndDistrictCouncil |
| 228 | StHelensBC |
| 229 | StaffordBoroughCouncil |
| 230 | StaffordshireMoorlandsDistrictCouncil |
| 231 | StevenageBoroughCouncil |
| 232 | StockportBoroughCouncil |
| 233 | StokeOnTrentCityCouncil |
| 234 | StratfordUponAvonCouncil |
| 235 | StroudDistrictCouncil |
| 236 | SunderlandCityCouncil |
| 237 | SurreyHeathBoroughCouncil |
| 238 | SwanseaCouncil |
| 239 | TamesideMBCouncil |
| 240 | TandridgeDistrictCouncil |
| 241 | TeignbridgeCouncil |
| 242 | TelfordAndWrekinCouncil |
| 243 | TendringDistrictCouncil |
| 244 | TestValleyBoroughCouncil |
| 245 | TewkesburyBoroughCouncil |
| 246 | ThanetDistrictCouncil |
| 247 | ThreeRiversDistrictCouncil |
| 248 | ThurrockCouncil |
| 249 | TonbridgeAndMallingBC |
| 250 | TorbayCouncil |
| 251 | TorridgeDistrictCouncil |
| 252 | TunbridgeWellsCouncil |
| 253 | UttlesfordDistrictCouncil |
| 254 | ValeofGlamorganCouncil |
| 255 | ValeofWhiteHorseCouncil |
| 256 | WakefieldCityCouncil |
| 257 | WalsallCouncil |
| 258 | WandsworthCouncil |
| 259 | WarringtonBoroughCouncil |
| 260 | WarwickDistrictCouncil |
| 261 | WatfordBoroughCouncil |
| 262 | WaverleyBoroughCouncil |
| 263 | WealdenDistrictCouncil |
| 264 | WelhatCouncil |
| 265 | WestBerkshireCouncil |
| 266 | WestDunbartonshireCouncil |
| 267 | WestLancashireBoroughCouncil |
| 268 | WestLindseyDistrictCouncil |
| 269 | WestLothianCouncil |
| 270 | WestNorthamptonshireCouncil |
| 271 | WestOxfordshireDistrictCouncil |
| 272 | WestSuffolkCouncil |
| 273 | WiganBoroughCouncil |
| 274 | WiltshireCouncil |
| 275 | WinchesterCityCouncil |
| 276 | WokingBoroughCouncil |
| 277 | WokinghamBoroughCouncil |
| 278 | WolverhamptonCityCouncil |
| 279 | WorcesterCityCouncil |
| 280 | WrexhamCountyBoroughCouncil |
| 281 | WychavonDistrictCouncil |
| 282 | WyreCouncil |
| 283 | WyreForestDistrictCouncil |
| 284 | YorkCouncil |
