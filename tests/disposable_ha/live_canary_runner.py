"""One-shot, redaction-safe South Kesteven public-fixture canary runner.

This module is intentionally not part of the normal test suite's network path.
Running ``main`` requires both a deliberate command-line acknowledgement and a
fixed environment acknowledgement.  Those controls record intent for the single
plan-approved run; they are not an additional approval gate. Address values can
only come from the repository's already-public
``uk_bin_collection/tests/input.json`` entry.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

COUNCIL_NAME = "SouthKestevenDistrictCouncil"
PUBLIC_FIXTURE_PATH = Path("/workspace/uk_bin_collection/tests/input.json")
PUBLIC_BINDAY_URL = "https://www.southkesteven.gov.uk/binday"
SELENIUM_INTERNAL_URL = "http://selenium:4444"
APPROVAL_ENVIRONMENT_VARIABLE = "UKBCD_LIVE_CANARY_APPROVED"
APPROVAL_VALUE = "one-public-fixture-lookup"
LOCK_PATH = Path("/tmp/ukbcd-live-canary-one-shot.lock")
MINIMUM_START_DELAY_SECONDS = 5.0

_URL_PATTERN = re.compile(r"(?i)\bhttps?://[^\s\"'<>]+")
_UK_POSTCODE_PATTERN = re.compile(
    r"(?i)\b(?:GIR\s?0AA|(?:[A-Z]{1,2}[0-9][0-9A-Z]?)\s?[0-9][A-Z]{2})\b"
)
_HOUSEHOLD_IDENTIFIER_PATTERN = re.compile(
    r"(?i)\b((?:uprn|usrn)\s*[:=]?\s*)[0-9]{6,15}\b"
)


@dataclass(frozen=True)
class PublicFixture:
    """The public South Kesteven canary fields committed to input.json."""

    postcode: str
    house_number: str
    url: str
    web_driver: str


def load_public_fixture(path: Path = PUBLIC_FIXTURE_PATH) -> PublicFixture:
    """Load and fail-closed validate the repository's public fixture."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    entry = raw.get(COUNCIL_NAME)
    if not isinstance(entry, dict):
        raise ValueError("public South Kesteven fixture is missing")

    postcode = entry.get("postcode")
    house_number = entry.get("house_number")
    url = entry.get("url")
    web_driver = entry.get("web_driver")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (postcode, house_number, url, web_driver)
    ):
        raise ValueError("public South Kesteven fixture is incomplete")
    if entry.get("skip_get_url") is not True:
        raise ValueError(
            "public South Kesteven fixture must skip the generic HTTP preflight"
        )
    if url != PUBLIC_BINDAY_URL:
        raise ValueError("public South Kesteven URL changed from the reviewed origin")

    driver = urlsplit(web_driver)
    if (
        driver.scheme != "http"
        or driver.hostname != "selenium"
        or driver.port != 4444
        or driver.path not in {"", "/"}
        or driver.query
        or driver.fragment
        or driver.username is not None
        or driver.password is not None
    ):
        raise ValueError("public WebDriver fixture is not the isolated Selenium alias")

    return PublicFixture(
        postcode=postcode.strip(),
        house_number=house_number.strip(),
        url=url,
        web_driver=SELENIUM_INTERNAL_URL,
    )


def redact_output(value: object, fixture: PublicFixture | None = None) -> str:
    """Remove household values and all URLs from text intended for output."""
    text = str(value)
    text = _URL_PATTERN.sub("[REDACTED_URL]", text)
    text = _UK_POSTCODE_PATTERN.sub("[REDACTED_POSTCODE]", text)
    text = _HOUSEHOLD_IDENTIFIER_PATTERN.sub(r"\1[REDACTED]", text)

    if fixture is not None:
        explicit_values = {
            fixture.postcode,
            fixture.postcode.replace(" ", ""),
            fixture.house_number,
            fixture.url,
            fixture.web_driver,
        }
        for sensitive in sorted(explicit_values, key=len, reverse=True):
            if not sensitive:
                continue
            text = re.sub(re.escape(sensitive), "[REDACTED]", text, flags=re.I)
    return text


def parse_collection_result(result: object) -> dict[str, object]:
    """Return a deliberately non-identifying summary of collector JSON."""
    payload = json.loads(result) if isinstance(result, str) else result
    if not isinstance(payload, dict) or not isinstance(payload.get("bins"), list):
        raise ValueError("collector did not return a bins list")
    bins = payload["bins"]
    for row in bins:
        if not isinstance(row, dict):
            raise ValueError("collector returned a malformed bin row")
        if not isinstance(row.get("type"), str) or not isinstance(
            row.get("collectionDate"), str
        ):
            raise ValueError("collector returned an incomplete bin row")
    return {
        "status": "passed",
        "council": COUNCIL_NAME,
        "logical_lookups": 1,
        "bin_count": len(bins),
    }


def _invoke_collector(fixture: PublicFixture) -> object:
    """Invoke the production CLI application once using only public values."""
    from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp

    app = UKBinCollectionApp()
    app.set_args(
        [
            COUNCIL_NAME,
            fixture.url,
            "--postcode",
            fixture.postcode,
            "--number",
            fixture.house_number,
            "--skip_get_url",
            "--web_driver",
            fixture.web_driver,
        ]
    )
    return app.run()


def reserve_one_shot(path: Path = LOCK_PATH) -> None:
    """Fail if this immutable canary container already attempted its lookup."""
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="ascii") as lock_file:
        lock_file.write("reserved\n")


def run_canary(
    fixture: PublicFixture,
    *,
    invoke: Callable[[PublicFixture], object] = _invoke_collector,
    sleeper: Callable[[float], None] = time.sleep,
    minimum_delay_seconds: float = MINIMUM_START_DELAY_SECONDS,
) -> dict[str, object]:
    """Perform exactly one deliberately delayed logical lookup."""
    if minimum_delay_seconds < MINIMUM_START_DELAY_SECONDS:
        raise ValueError("live canary delay cannot be reduced below five seconds")
    sleeper(minimum_delay_seconds)

    # Do not allow third-party or legacy print/log output to escape.  Only the
    # fixed summary below is emitted by main().
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        result = invoke(fixture)
    return parse_collection_result(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm-one-public-fixture-lookup",
        action="store_true",
        help="Required acknowledgement for the one plan-approved live canary.",
    )
    args = parser.parse_args()

    if (
        not args.confirm_one_public_fixture_lookup
        or os.environ.get(APPROVAL_ENVIRONMENT_VARIABLE) != APPROVAL_VALUE
    ):
        parser.error(
            "live canary requires the command acknowledgement and fixed approval environment value"
        )

    fixture: PublicFixture | None = None
    try:
        reserve_one_shot()
        fixture = load_public_fixture()
        summary = run_canary(fixture)
        print(json.dumps(summary, sort_keys=True))
        return 0
    except Exception as exc:
        # Never emit a traceback or arbitrary response content.  The class and a
        # short redacted message are enough to correlate with separately-redacted
        # scraper diagnostics.
        message = redact_output(exc, fixture)[:240]
        failure = {
            "status": "failed",
            "council": COUNCIL_NAME,
            "logical_lookups": 0 if fixture is None else 1,
            "error_type": type(exc).__name__,
            "message": message,
        }
        print(json.dumps(failure, sort_keys=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
