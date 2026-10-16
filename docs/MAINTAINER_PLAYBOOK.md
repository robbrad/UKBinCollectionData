# UKBinCollectionData maintenance playbook (for a future Claude session)

Distilled from the Sept/Oct 2026 passes (PRs #2242, #2268, #2269, #2272). Read all of it
before touching anything; §0 and §11 are checklists you can run straight through.

---

## 0. Session-start checklist

1. `git fetch origin master && git branch -f master origin/master`. A stale local
   `master` makes small PRs look like 25-file diffs.
2. Check that the **last release actually shipped**. In the latest `Release - Bump Version`
   run on master, the conclusion should be `success` and a `bump: version X → Y` commit
   should exist:
   `gh api "repos/robbrad/UKBinCollectionData/actions/runs?branch=master&per_page=15" --jq '.workflow_runs[]|[.name,.head_sha[0:7],.conclusion]|@tsv'`
3. List open PRs and open issues. Read **every comment** on each, not just the body.
   Reporters often post the root cause, a working curl, or a second council with the same
   failure.
4. Skim the root-level `ISSUE_RESOLUTION_PROGRESS.md` and `CI_FAILURE_TRIAGE.md`. They
   record earlier triage, including councils already known to be blocked.

---

## 1. Repo shape: what a "council" actually is

Each council needs **two things kept in sync**:

| Piece | Path | Consumed by |
|---|---|---|
| Scraper class | `uk_bin_collection/uk_bin_collection/councils/<Name>.py` | CLI, HA integration, API server |
| Config entry | `uk_bin_collection/tests/input.json`, key = `<Name>` exactly | see §5 (it does much more than test data) |

Shared base classes, such as `SocietyWorks.py`, live in `councils/` but are not councils.
They are listed in `NON_COUNCIL_FILES` in `council_feature_input_parity.py` instead of
getting an input.json entry.

---

## 2. The sandbox can't reach council sites, so CI does the live testing

### How the PR integration job really works (`.github/workflows/behave_pull_request.yml`)

- It triggers on `pull_request` to master only, never on a plain branch push. A **draft PR**
  also triggers it, so open diagnostic PRs as drafts.
- `paths-ignore` covers `**/*.md`, `wiki/**` and `uk_bin_collection_api_server/**`. A PR that
  only touches those runs no tests.
- **What it live-tests depends on which `councils/*.py` files the PR changed.** The
  changed basenames are joined into `pytest -k "A or B or C"`. Consequences:
  - **If no council file changed at all**, the list is empty and the Makefile runs the
    **entire live suite**, about 350 councils. That takes a long time and many fail on IP
    blocks. Examples are a PR touching only `common.py`, `input.json`, workflows, or a
    base class on its own. Don't mistake the resulting failures for regressions.
  - If council files changed, **only those** run. A base-class basename such as
    `SocietyWorks` in the `-k` list matches no `input.json` key, so its subclasses
    aren't tested. The October SocietyWorks UA fix was never live-tested for this
    reason. To cover dependents, make a trivial change to one subclass file in a
    throwaway diagnostic PR.
  - To diagnose a council you haven't fixed yet, the diagnostic print in its `.py` *is*
    what puts it in the matrix.
- **The integration step has `continue-on-error: true`**, so the check run is green even
  when councils fail. Never read "Run Integration Tests ✅" as "passed". Always read the
  pytest summary line (`N failed, M passed`) in the log (§3).

### The diagnostic loop

1. Add `print("[diagnostic] ...")` lines covering status code, `response.url` after
   redirects, page title, and candidate links or selectors. **Batch every council you're
   investigating into one draft PR per round.** One CI run then tests them all in parallel.
2. Push, wait about 3 to 5 minutes for "Run Integration Tests", then parse the log (§3).
3. Fix, **delete the diagnostics**, push, and re-check.
4. If a diagnostic led nowhere, revert the file completely
   (`git checkout origin/master -- <file>`) and confirm the diff is empty.

---

## 3. Reading CI logs efficiently

- `mcp__github__get_job_logs` with `return_content: true` usually exceeds the output limit
  and gets saved to a file. That's fine: parse the file, don't Read it.
- Built-in `gh api` can list runs, jobs and job **steps**
  (`repos/.../actions/jobs/<id>` → `.steps[]`) and **annotations**. It can't fetch log
  bodies, because those redirect to blob storage. Use the MCP tool for log content.

Reusable parser. Save it once and pass it the saved file path:

```python
# parse_ci_log.py  — usage: python3 -I parse_ci_log.py <saved-tool-result.txt> [Council ...]
import json, re, sys, warnings
warnings.filterwarnings("ignore")
raw = open(sys.argv[1]).read()
try: logs = json.loads(raw)["logs_content"]
except Exception: logs = raw
logs = logs.encode().decode("unicode_escape", errors="ignore")
print(*re.findall(r"=+ .*(?:passed|failed).* =+", logs), sep="\n")
print("FAILED:", sorted(set(re.findall(r"FAILED .*?\[(\w+)\]", logs))))
for name in sys.argv[2:]:
    for m in re.finditer(rf"_+ test_scenario_outline\[{name}\] _+", logs):
        print(logs[m.start(): m.start() + 6000])
print(*sorted(set(re.findall(r"\[diagnostic\][^\n]*", logs))), sep="\n")
```

---

## 4. A dead end that keeps coming back: CI IPs are blocked

Some council WAFs block GitHub-runner IPs whatever the client does:

- **Cloudflare**: a 403 with `cf-mitigated: challenge`, or a "Just a moment..." page even
  for real Selenium. Seen on Sunderland, Gateshead, Stockton-on-Tees and Boston.
- **Azure App Gateway**: a bare 403 from `Microsoft-Azure-Application-Gateway/v2`. Seen on
  Exeter and Teignbridge.

Try each of these **once**:

- `from curl_cffi import requests as cffi_requests` with
  `cffi_requests.Session(impersonate="chrome")`. This fixed Sunderland for real users
  even though CI still got a 403.
- The stealth flags already in `create_webdriver()` in `common.py`, now on by default.

If CI still fails after that, stop. Ship the change as a "best-effort, unverifiable from CI"
fix. Reference the issue with `Targets #N`, not `Fixes #N`, so it stays open, and ask the
reporter to confirm (§8).

### Blazor Server sites: a missing link doesn't mean missing data

A Blazor Server page (look for `_framework/blazor.server.js` and a `wss://.../_blazor`
WebSocket) runs its logic on the server, so a URL can exist without ever appearing in
the DOM. Isle of Wight's calendar `<a class="download">` became
`<button>View Collection Calendar</button>` with no href. The URL was still there: the
server called a one-line JS interop helper, found by reading the site's own script
(`/js/WasteDay/wasteDay.js`), which built an `<a download href="...pdf">` and clicked it.

So before concluding a council has withdrawn its data:

- Read the site's own `/js/**` files. They are small and they name the interop helpers.
- Hook the sink, click the control, and read the URL back out with `execute_script`.
  Hook **`HTMLAnchorElement.prototype.click`**, not the named interop function: Blazor
  caches the function it resolved off `window`, so replacing that function has no effect
  once the page has invoked it once. Hooking the anchor also stops a real download.
- Driving one of these by hand: setting an input's `value` from JS does **not** register,
  because Blazor re-renders and discards it. Type with the keyboard. For a `<select>`,
  setting `value` plus a dispatched `new Event("change", {bubbles: true})` does work.
- Expect a `StaleElementReferenceException` on the first render: the static server render
  is replaced wholesale when SignalR hydrates. Re-fetch the element after it settles.

---

## 5. input.json: the part most easily got wrong

`input.json` is **not just test fixtures**. It has four consumers:

1. **Integration tests**: `test_validate_council.py` parametrises over its keys and
   passes `url`, `uprn`, `postcode`, `house_number`/`paon`, `web_driver` and
   `skip_get_url` to the scraper.
2. **The Home Assistant config flow**: `custom_components/uk_bin_collection/const.py`
   `INPUT_JSON_URL` fetches input.json **from the release tag**, e.g. `.../0.172.5/...`.
   The fields present decide which inputs the HA UI shows the user. For example,
   `web_driver` present means a Selenium URL field, and `skip_get_url` hides the URL field
   unless `custom_component_show_url_field` is set. Because it's pinned to a tag, an
   input.json change only reaches HA users **after a release**.
3. **The wiki**: `wiki/generate_wiki.py` builds the council list from `wiki_name` and
   `wiki_note`. `wiki.yml` runs it on master pushes that touch input.json.
4. **The coverage map**: `LAD24CD` is the ONS local-authority code.

Fields in use: `url` and `wiki_name` are always present. `wiki_note`, `LAD24CD` and
`skip_get_url` are almost always present. Then `uprn`, `postcode`, `house_number`,
`web_driver` (required if the class calls `create_webdriver`), `wiki_command_url_override`,
and occasionally `paon` or `custom_component_show_url_field`.

**Rules:**

- **Change a scraper's inputs, change input.json in the same commit.** Examples: UPRN
  becomes postcode + house number (Rhondda Cynon Taff, #2262, will need this), or a
  scraper stops or starts using Selenium. Update the fields *and* the `wiki_note`. If you
  don't, HA asks users for the wrong things and the integration test sends the wrong args.
- Add `web_driver: "http://selenium:4444"` if and only if the scraper uses
  `create_webdriver`. `tests/check_selenium_url_in_input.json.py` checks this.
- Test data is **public**. Use a council office, library or other non-residential address,
  never a reporter's home address from an issue.
- New council: the key must equal the class filename. Add `LAD24CD`. Keep fields
  alphabetical within the entry. The file isn't globally sorted, so put the new entry near
  its neighbours.
- `collect_data.py ... -d` (dev mode) writes or updates the council's entry from a real
  run. It's handy but **review the diff**.

### Parity check: what it really does

`council_feature_input_parity.py` checks **one thing**: the set of `councils/*.py`
basenames (minus `NON_COUNCIL_FILES` and `RETIRED_COUNCILS`) equals the set of
input.json keys. Despite the CI step's name, it doesn't look at the feature file or at
field correctness.

**It reads from the GitHub API, not your working tree.** `make parity-check` without
`repo=… branch=…` checks **master**. So either push first and run
`make parity-check repo=robbrad/UKBinCollectionData branch=<your-branch>`, or use this
offline equivalent, which works in the sandbox:

```bash
poetry run python - <<'EOF'
import importlib, json, pathlib
# Read the exclusions out of the real check so this can't drift from it.
# Needs the project's venv, since the parity module imports requests.
parity = importlib.import_module("uk_bin_collection.tests.council_feature_input_parity")
excluded = {"__init__"} | parity.NON_COUNCIL_FILES | parity.RETIRED_COUNCILS
files = {p.stem for p in pathlib.Path("uk_bin_collection/uk_bin_collection/councils").glob("*.py")} - excluded
keys = set(json.load(open("uk_bin_collection/tests/input.json")))
print("missing from input.json:", sorted(files - keys)); print("no class file:", sorted(keys - files))
EOF
jq empty uk_bin_collection/tests/input.json && echo "input.json is valid JSON"
```

(Add a new base class to `NON_COUNCIL_FILES` and a retired council to
`RETIRED_COUNCILS`; the snippet reads both, so there's nothing to keep in step here.
§9a has a longer version that also checks the `web_driver` field.)

### Retiring a council

When a council puts its bin lookup behind a login and no public endpoint is left, don't
delete the class file - `collect_data.import_council_module` imports it by the name
stored verbatim in each HA user's saved config, so deleting it turns an explainable
failure into an `ImportError`. Instead:

1. Replace the body of `councils/<Council>.py` with a `CouncilClass` whose `parse_data`
   raises immediately, with a message naming and linking the portal that replaced it, and
   a docstring giving the reason and the date.
2. Remove the entry from `input.json`, so the live suite stops testing it and the HA
   config flow stops offering it to new users.
3. Add the class name to `RETIRED_COUNCILS` in `council_feature_input_parity.py` (not to
   `NON_COUNCIL_FILES` - that's for shared base classes). The offline snippets read that
   set, so there's nothing else to update.
4. Add an offline test asserting the error message, as in `test_fylde_council.py`.

`wiki/Councils.md` is auto-generated from input.json by the `Deploy - Wiki` workflow on
master pushes, so leave it alone; it drops the council on merge. Existing HA users keep
their sensors until they remove the council from their config, but now get a message
that says why.

---

## 6. Consolidating contributor PRs

```bash
git fetch origin pull/<N>/head:pr-<N>
git diff --stat origin/master...pr-<N>       # scope check FIRST (three dots = merge-base)
git cherry-pick -n $(git merge-base origin/master pr-<N>)..pr-<N>
git diff --cached                            # review; fix obvious issues yourself
git commit                                   # conventional message + "(from #N, credit @author)"
```

- **Size rule**: exclude anything touching more than about 3 files or mixing unrelated
  councils. One huge multi-council PR went badly before. List exclusions and the reason in
  the release PR's "Not included" section.
- Don't include drafts.
- **Squashing with an explicit subject destroys the contributor's authorship.** Dropping
  `-n` from the cherry-pick above keeps them as the commit author, and a squash merge of a
  single-commit PR normally carries that through - *unless* you pass `--subject`/`--body`
  to `gh pr merge`, which re-authors the squashed commit to whoever merged. That happened
  to #2276 in 0.173.3: the contributor's fix is credited to the maintainer on master, and
  it can't be undone without rewriting history. So either let the squash take the PR's own
  title, or add an explicit `Co-authored-by:` trailer to the body. Either way, comment on
  their PR saying where it landed.
- Contributor PRs change the scraper but often **forget input.json** (§5). Check it.
- `git add -A` followed later by `git add <files>` still commits everything staged. If the
  file count looks wrong: `git reset --soft HEAD^ && git reset`, then redo.
- Keep **two branches**: a clean release branch with only cherry-picks and dependabot
  bumps, and a triage branch for the diagnostic loop. The noise of one never blocks the
  other.

---

## 7. Commits, merge titles and releases

The lesson from #2272: **every commit that lands on master must be a conventional commit,
including the squash-merge title.**

- `lint.yml` (commitlint) runs on PRs **and on pushes to master**. Use the types `fix`,
  `feat`, `chore`, `docs`, `ci`, `refactor`, `test`, `perf`, `build` and `revert`, with an
  optional `(scope)`.
- `bump.yml` runs `cz bump` on every master push not under `paths-ignore` (`*.md`, `wiki/**`,
  `.github/workflows/**`). Only `fix`, `feat`, `refactor`, `perf` and breaking changes are
  **releasable**. In October, squash titles like "October release: …" and "Fix East
  Lothian, …" were merged. commitizen saw no releasable commits (exit 21), the bump failed,
  and **the fixes sat unreleased**.
- Squash-merge title: `fix: October council fixes (Tower Hamlets, SocietyWorks, …)` or
  `fix(east-lothian): …`. Pass `commit_title` explicitly when calling
  `merge_pull_request`, and type a plain `&`, not `&amp;`. The MCP call escaped it once
  and that's now permanent in history.
- Release chain: `fix:` lands on master → bump commit plus tag `X.Y.Z` → `release.yml`
  publishes to PyPI (with the PyPI-propagation wait added in #2242), builds Docker, and
  bumps the HA manifest and `INPUT_JSON_URL`.
- **After every merge**, confirm `Release - Bump Version` succeeded and a new tag exists.
  If it failed, find out why before closing out.
- Attribution trailers on every commit, and the "Generated with Claude Code" footer on PR
  bodies, as given by the session's system reminder.

---

## 8. Issues: when and what to comment

Post **one substantive comment per issue per pass**. Don't post running commentary.

| Situation | Action | Comment should contain |
|---|---|---|
| Fixed and live-verified | PR body: `Fixes #N` | After merge: "Fixed in #PR, ships in the next release (X.Y.Z); HA users get it after updating." Verify that it auto-closed. |
| Fix shipped, unverifiable from CI (WAF) | `Targets #N`, leave open | What changed and why, and an ask: "please update to X.Y.Z and confirm" |
| Diagnosed, not fixable here | leave open | Root cause, **evidence** (status code, server header, final URL), and exactly what a fix needs: field names, endpoint, flow. Rhondda Cynon Taff #2262 is the model. |
| Needs info | leave open | Ask for the **public** details needed (postcode, council-site URL that works for them, full traceback). Don't ask for a home address in public. |
| Duplicate | close, `state_reason: duplicate`, `duplicate_of` | Link the canonical issue |
| Feature request outside current scope | leave open | Feasibility notes (e.g. "the API doesn't expose X") |

Auto-close gotcha: GitHub needs **a keyword for each issue**. `Fixes #2255, #2258, #2247`
closed only #2255. Write `Fixes #2255, fixes #2258, fixes #2247`. After merging, re-read
each claimed issue's state anyway.

Close superseded contributor and dependabot PRs with a thank-you comment ("cherry-picked
into #X with credit"), then close them. GitHub won't treat a cherry-pick as merging them.

---

## 9. Running tests locally

```bash
poetry install                       # or: make install-dev
make unit-tests                      # what CI runs; excludes live tests, includes HA component tests
# or a subset, ALWAYS excluding step_defs (those are the live tests):
poetry run pytest uk_bin_collection/tests custom_components/uk_bin_collection/tests \
    --ignore=uk_bin_collection/tests/step_defs/ -q
poetry run pytest uk_bin_collection/tests/test_<council>.py -q
poetry run black --check uk_bin_collection/uk_bin_collection/councils/<File>.py
```

- **Known sandbox-only failures, not bugs**: `test_check_postcode_valid` and
  `test_check_postcode_invalid` (need api.postcodes.io), and `test_create_webdriver_local`
  (chromedriver download). Mention them in the test plan and move on.
- **`black .` checks almost nothing in this repo.** `.gitignore` opens with `*`
  ("ignore everything") and then re-includes patterns like `!*.py`. black honours
  `.gitignore`, and no *directory* is re-included, so handing it a directory silently
  skips every subdirectory - `black .` sees two root-level files. Always pass the files
  you changed explicitly, e.g.
  `git diff --name-only origin/master..HEAD | grep '\.py$' | xargs poetry run black --check`.
  (`bin_to_ics.py` is already unformatted on master; leave it unless you're fixing it
  on purpose.)
- **Add an offline unit test for every parser fix.** Feed a saved or hand-built HTML snippet
  to the parsing function, as in `test_adur_and_worthing_councils.py` and
  `test_south_lanarkshire_council.py`. It's the only part of the fix the sandbox can verify,
  and it pins the new page shape.
- The live suite, `pytest uk_bin_collection/tests/step_defs/ -k <Council>`, can't reach
  sites from the sandbox. Use the CI loop (§2), or run it locally (§9a).

---

## 9a. Running the live suite locally (the fast path)

A session on a **UK residential connection** can run the whole live suite itself, in
about **9 minutes** for all ~352 councils. That is faster and far more informative than
the CI loop, and it is the only way to tell a real breakage from an IP or fingerprint
block. Prefer it whenever the machine has a UK connection and a real Chrome.

```bash
poetry env use python3.14 && make install-dev     # Python 3.14.2+ (the HA dev dep needs it)
make unit-tests                                   # must be 100% green here; no sandbox excuses
poetry run pytest uk_bin_collection/tests/step_defs/ -n 4 --local_browser True -q --tb=line --junit-xml=live.xml
```

- `--local_browser True` makes `create_webdriver` use the local Chrome instead of a grid.
  Install Chrome; `webdriver-manager` fetches a matching chromedriver on first run.
- **Always pass `--junit-xml`.** With `-n 4` the console output interleaves; the XML is
  the only reliable way to get per-council pass/fail and failure messages afterwards.
- **Always re-run the failures serially** before believing them:
  `pytest uk_bin_collection/tests/step_defs/ -k "A or B or C" --local_browser True`.
  In the October 2026 pass this turned 27 parallel failures into 24 real ones - Arun,
  St Helens and Wealden were purely concurrency noise.

### On Windows specifically

- There is no `make`; run the Makefile's commands directly (§9 lists them).
- `poetry env use python3.14` fails - no such executable. Use the full path:
  `poetry env use "$LOCALAPPDATA/Programs/Python/Python314/python.exe"`.
- Never run `chrome.exe --version` to check Chrome; it launches a browser window.
  Use `(Get-Item "C:\Program Files\Google\Chrome\Application\chrome.exe").VersionInfo.ProductVersion`.
- `check_selenium_url_in_input.json.py` crashes on a `UnicodeEncodeError` writing its
  tick characters to a cp1252 console. Prefix with `PYTHONIOENCODING=utf-8`. It also
  reads from the **GitHub API**, like the parity check (§5), so it checks master and
  silently checks nothing at all when rate-limited. Use this offline equivalent:

```bash
poetry run python - <<'EOF'
import importlib, json, pathlib
# Read the exclusions out of the real check so this can't drift from it.
parity = importlib.import_module("uk_bin_collection.tests.council_feature_input_parity")
excluded = {"__init__"} | getattr(parity, "NON_COUNCIL_FILES", set()) \
                        | getattr(parity, "RETIRED_COUNCILS", set())
root = pathlib.Path("uk_bin_collection/uk_bin_collection/councils")
data = json.load(open("uk_bin_collection/tests/input.json"))
files = {p.stem: p.read_text(encoding="utf-8") for p in root.glob("*.py")
         if p.stem not in excluded}
print("missing from input.json:", sorted(set(files) - set(data)))
print("no class file:", sorted(set(data) - set(files)))
for name, src in sorted(files.items()):
    uses, has = "create_webdriver" in src, "web_driver" in data.get(name, {})
    if uses != has:
        print(f"  web_driver mismatch: {name} uses={uses} has={has}")
EOF
```

### "Cloudflare / WAF block" is usually not about the IP

Before concluding that a council blocks the runner's IP, check what actually blocks it.
Most of the October 2026 "Cloudflare challenge in CI" list was a **client fingerprint**
problem reproducible anywhere:

| Symptom | Real cause | What works |
|---|---|---|
| 403 + `server: Microsoft-Azure-Application-Gateway/v2` | the default `python-requests` User-Agent | `headers={"User-Agent": get_scraper_user_agent()}` (Herefordshire, East Devon) |
| 403 + `server: cloudflare`, `cf-mitigated: challenge` on a plain GET | TLS/JA3 fingerprint | `curl_cffi.requests.Session(impersonate="chrome")` |
| Selenium reaches the form, then times out on the **next** step, page title `Just a moment...` | the scraper's hardcoded UA claims a stale Chrome version and/or the wrong OS | fixed centrally in `create_webdriver` (§9b) |
| `Just a moment...` even with a correct UA and a real local Chrome | Cloudflare Turnstile | needs `undetected-chromedriver`, non-headless |

Diagnose it in one shot rather than guessing - compare a plain `requests` GET against a
`curl_cffi` impersonated one and read `status`, `server` and `cf-mitigated`.

## 9b. Scraper User-Agents: do not hardcode a Chrome version

Most Selenium councils pass a literal UA such as
`"Mozilla/5.0 (X11; Linux x86_64) ... Chrome/138.0.0.0 Safari/537.36"`. Both halves rot:
the version goes stale, and the platform token is wrong on any OS but the author's.
Cloudflare compares both against what the browser's own JavaScript reports, and serves
an interstitial on the mismatch - on GOSS iCM sites it arrives on the **form POST**, so
the scraper gets through the postcode step and then times out waiting for the address
dropdown. That reads exactly like a selector change, which is how these ended up
mis-triaged as IP blocks.

`create_webdriver` now rewrites a local driver's UA to the real Chrome major version and
this OS's platform token (`align_user_agent_to_browser`). A **remote** grid's Chrome is
whatever its image ships, so a remote caller's UA is passed through untouched - keep that
in mind when CI and a local run disagree.

When writing a new Selenium scraper, pass a plain modern UA and let `create_webdriver`
align it. Don't try to out-clever it per council.

---

## 10. Working faster

- **Batch diagnostics.** Put all suspect councils in one draft PR per round, not one PR
  per council.
- **Don't sleep-poll CI.** Subscribe to PR activity, or run a single background wait, and
  do other work (issue comments, unit tests, parity) meanwhile.
- **Parallelise independent councils** with sub-agents, each given the council file,
  the issue text and the CI log excerpt. Keep the git work and the PR in the main session.
- **Triage cheaply before reaching for CI.** Many fixes are obvious from the traceback
  alone, e.g. a renamed label or a redirected URL. Use the CI loop only when the cause is
  unknown.
- **Keep the paper trail in the repo.** Append the pass's outcome to
  `ISSUE_RESOLUTION_PROGRESS.md` so the next session starts with the known-blocked list.

---

## 11. End-of-pass checklist

- [ ] Every merged squash title is a conventional `fix:` or `feat:` (§7)
- [ ] `Release - Bump Version` succeeded and the new tag exists, and `release.yml` published
      to PyPI
- [ ] Every `Fixes #N` issue is actually closed. Close stragglers manually with a comment.
- [ ] Superseded contributor and dependabot PRs are closed with a credit comment
- [ ] Every unfixed issue touched has one evidence-bearing comment (§8)
- [ ] input.json matches every scraper whose inputs changed (§5), and parity is clean
- [ ] No `[diagnostic]` prints left on master: `git grep -n "\[diagnostic\]"`
- [ ] Progress notes appended to `ISSUE_RESOLUTION_PROGRESS.md`
