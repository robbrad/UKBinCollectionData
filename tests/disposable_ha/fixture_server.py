"""Loopback-only deterministic HTML service for the South Kesteven browser flow."""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8081
EVIDENCE = Path(os.environ.get("UKBCD_TEST_EVIDENCE_DIR", "/evidence"))


def _future_date(days: int) -> str:
    return (date.today() + timedelta(days=days)).strftime("%A %d %B, %Y")


def _checker_html() -> str:
    first_date = _future_date(7)
    second_date = _future_date(14)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Offline bin checker</title></head>
<body>
  <input id="current-section-id" value="488" type="hidden">
  <main id="body-content">
    <label for="FF5265-text">Postcode</label>
    <input id="FF5265-text" name="postcode" autocomplete="postal-code">
    <button id="FF5265-find" type="button" onclick="showAddresses()">Find</button>
    <select id="FF5265-list" name="address" style="display:none"
            onchange="confirmAddress()"></select>
    <input id="FF5265" name="uprn" value="" type="hidden">
    <span id="FF5265-displayname"></span>
    <button id="FF5265-change" type="button" style="display:none">Change</button>
    <button id="submit-button" type="button" onclick="showResults()">Continue</button>
  </main>
  <script>
    function showAddresses() {{
      const select = document.getElementById('FF5265-list');
      select.innerHTML = '<option value=""></option>' +
        '<option value="fixture-other">Other Test House, Grantham</option>' +
        '<option value="fixture-codex">Codex Test House, Grantham</option>';
      select.style.display = 'block';
    }}
    function confirmAddress() {{
      const select = document.getElementById('FF5265-list');
      document.getElementById('FF5265').value = select.value;
      document.getElementById('FF5265-displayname').textContent =
        select.options[select.selectedIndex].text;
      document.getElementById('FF5265-change').style.display = 'block';
    }}
    function showResults() {{
      document.getElementById('current-section-id').value = '489';
      document.getElementById('body-content').innerHTML = `
        <h1>Your Collections</h1>
        <table class="Alloy-table">
          <tr><td>{first_date}</td><td>240 Litre Refuse</td></tr>
          <tr><td>{second_date}</td><td>240 Litre Recycling</td></tr>
        </table>`;
    }}
  </script>
</body></html>"""


def _is_fixture_browser_user_agent(value: str) -> bool:
    """Require the disposable browser marker, not merely a generic browser UA."""
    normalized = value.casefold()
    return "mozilla" in normalized and "ukbcd-disposable-fixture" in normalized


class Handler(BaseHTTPRequestHandler):
    """Serve only the three fixture routes needed by the validation."""

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        with (EVIDENCE / "fixture_requests.jsonl").open(
            "a", encoding="utf-8"
        ) as handle:
            user_agent = self.headers.get("User-Agent", "").lower()
            handle.write(
                json.dumps(
                    {
                        "path": self.path.split("?", 1)[0],
                        "browser": "mozilla" in user_agent,
                        "custom_user_agent": "ukbcd-disposable-fixture" in user_agent,
                    },
                    sort_keys=True,
                )
                + "\n"
            )

        if self.path == "/health":
            self._send(200, "text/plain", "ok")
            return
        if self.path == "/binday":
            user_agent = self.headers.get("User-Agent", "")
            if not _is_fixture_browser_user_agent(user_agent):
                self._send(403, "text/html", "<h1>403 Forbidden</h1>")
                return
            self._send(
                200,
                "text/html",
                '<a href="http://127.0.0.1:8081/checker">'
                "Postcode bin day checker</a>",
            )
            return
        if self.path == "/checker":
            self._send(200, "text/html", _checker_html())
            return
        if self.path == "/static":
            self._send(200, "application/json", '{"fixture": true}')
            return
        self._send(404, "text/plain", "not found")

    def _send(self, status: int, content_type: str, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:
        del format, args


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
