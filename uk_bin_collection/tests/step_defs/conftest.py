# DIAGNOSTIC ONLY - never merge. Records every HTTP response and the final
# Selenium page state per council, then prints them for failed councils.
import json
import os
import pathlib
import re

import pytest

FULL = bool(os.environ.get("UKBCD_DIAG_FULL"))
BODY_MAX = 25000

DIAG_DIR = pathlib.Path("build/diag")
_current = {"council": None}
_failed = set()


def _record(entry):
    council = _current["council"]
    if not council:
        return
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    with open(DIAG_DIR / f"{council}.jsonl", "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def _summarise_html(text):
    title = re.search(r"<title[^>]*>(.*?)</title>", text or "", re.S | re.I)
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text or "", flags=re.S | re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    ids = re.findall(r"<(?:form|select|input|iframe)[^>]*?(?:id|name)=\"([^\"]+)\"", text or "", re.I)
    return (title.group(1).strip()[:80] if title else ""), body[:220], ids[:15]


def _install():
    import requests

    orig_send = requests.Session.send

    def send(self, request, **kwargs):
        try:
            resp = orig_send(self, request, **kwargs)
        except Exception as e:
            _record({"k": "req-err", "m": request.method, "u": request.url, "e": repr(e)[:800]})
            raise
        try:
            ct = resp.headers.get("Content-Type", "")
            t, b, ids = _summarise_html(resp.text if "html" in ct or "text" in ct or "json" in ct else "")
            _record({"k": "req", "m": request.method, "u": request.url[:160], "s": resp.status_code,
                     "srv": resp.headers.get("Server", ""), "cf": resp.headers.get("cf-mitigated", ""),
                     "ct": ct[:40], "loc": resp.headers.get("Location", "")[:120], "n": len(resp.content),
                     "title": t, "ids": ids, "body": b,
                     **({"full": resp.text[:BODY_MAX]} if FULL else {})})
        except Exception:
            pass
        return resp

    requests.Session.send = send

    try:
        from selenium.webdriver.remote.webdriver import WebDriver

        orig_quit = WebDriver.quit

        def quit(self):
            try:
                info = self.execute_script(
                    "return {u: location.href, t: document.title,"
                    " b: (document.body ? document.body.innerText : '').replace(/\\s+/g,' ').slice(0,300),"
                    " ids: Array.from(document.querySelectorAll('form,select,input,button,iframe'))"
                    ".map(e => e.tagName.toLowerCase()+'#'+(e.id||e.name||'')).slice(0,25)};"
                )
                if FULL:
                    info["src"] = self.page_source[:BODY_MAX]
                _record({"k": "selenium-final", **info})
            except Exception as e:
                _record({"k": "selenium-final-err", "e": repr(e)[:200]})
            return orig_quit(self)

        WebDriver.quit = quit
    except Exception:
        pass


if os.environ.get("UKBCD_DIAG"):
    _install()


@pytest.fixture(autouse=True)
def _diag_council(request):
    callspec = getattr(request.node, "callspec", None)
    _current["council"] = callspec.params.get("council") if callspec else None
    yield
    _current["council"] = None


def pytest_runtest_logreport(report):
    if report.failed:
        m = re.search(r"\[(\w+)\]", report.nodeid)
        if m:
            _failed.add(m.group(1))


def pytest_terminal_summary(terminalreporter):
    if not os.environ.get("UKBCD_DIAG"):
        return
    tr = terminalreporter
    tr.section("UKBCD diagnostics")
    for council in sorted(_failed):
        tr.write_line(f"### {council}")
        path = DIAG_DIR / f"{council}.jsonl"
        if not path.exists():
            tr.write_line("  (no requests recorded)")
            continue
        lines = path.read_text().splitlines()
        for line in (lines if FULL else lines[-12:]):
            tr.write_line("  " + (line if FULL else line[:700]))
