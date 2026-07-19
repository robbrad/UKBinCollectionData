"""Offline-only tests for the live-canary policy and redaction helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.disposable_ha.fixture_server import _is_fixture_browser_user_agent
from tests.disposable_ha.live_allowlist_proxy import (
    ALLOWED_HOSTS,
    ProxyRateLimitExceeded,
    ProxyRequestDenied,
    RequestLimiter,
    parse_proxy_request,
    safe_log_line,
)


def test_fixture_rejects_legacy_generic_get_user_agent() -> None:
    legacy = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/108.0.0.0 Safari/537.36"
    )
    configured = "Mozilla/5.0 UKBCD-Disposable-Fixture"

    assert _is_fixture_browser_user_agent(legacy) is False
    assert _is_fixture_browser_user_agent(configured) is True


from tests.disposable_ha.live_canary_runner import (
    COUNCIL_NAME,
    MINIMUM_START_DELAY_SECONDS,
    PUBLIC_BINDAY_URL,
    PublicFixture,
    load_public_fixture,
    parse_collection_result,
    redact_output,
    run_canary,
)


@pytest.mark.parametrize(
    "authority",
    [
        "www.southkesteven.gov.uk:443",
        "selfservice.southkesteven.gov.uk:443",
        "www.southkesteven.gov.uk:80",
        "selfservice.southkesteven.gov.uk:80",
    ],
)
def test_proxy_allows_only_reviewed_connect_authorities(authority: str) -> None:
    request = parse_proxy_request(
        f"CONNECT {authority} HTTP/1.1\r\nHost: redacted.invalid\r\n\r\n".encode()
    )

    assert request.is_tunnel is True
    assert request.host in ALLOWED_HOSTS
    assert request.port in {80, 443}
    assert request.forward_header is None


@pytest.mark.parametrize(
    "target",
    [
        "evil.example:443",
        "www.southkesteven.gov.uk.evil.example:443",
        "127.0.0.1:443",
        "www.southkesteven.gov.uk:22",
        "user@www.southkesteven.gov.uk:443",
        "[::1]:443",
    ],
)
def test_proxy_denies_non_allowlisted_connect_targets(target: str) -> None:
    with pytest.raises(ProxyRequestDenied):
        parse_proxy_request(f"CONNECT {target} HTTP/1.1\r\n\r\n".encode())


def test_proxy_rewrites_allowed_http_but_safe_log_has_no_request_data() -> None:
    sensitive_path = "/binday?postcode=NG31%208XG&number=43"
    request = parse_proxy_request(
        (
            "POST http://www.southkesteven.gov.uk"
            f"{sensitive_path} HTTP/1.1\r\n"
            "Host: attacker.invalid\r\n"
            "Proxy-Authorization: secret\r\n"
            "Content-Length: 0\r\n\r\n"
        ).encode()
    )

    assert request.is_tunnel is False
    assert request.host == "www.southkesteven.gov.uk"
    assert sensitive_path.encode() in request.forward_header
    assert b"attacker.invalid" not in request.forward_header
    assert b"Proxy-Authorization" not in request.forward_header

    log_line = safe_log_line(request.host, 200)
    assert log_line == "host=www.southkesteven.gov.uk status=200"
    assert "/binday" not in log_line
    assert "postcode" not in log_line
    assert "NG31" not in log_line
    assert "43" not in log_line


@pytest.mark.parametrize(
    "request_line",
    [
        "GET http://evil.example/path HTTP/1.1",
        "GET https://www.southkesteven.gov.uk/path HTTP/1.1",
        "DELETE http://www.southkesteven.gov.uk/path HTTP/1.1",
        "GET /relative HTTP/1.1",
    ],
)
def test_proxy_denies_unsafe_http_forms(request_line: str) -> None:
    with pytest.raises(ProxyRequestDenied):
        parse_proxy_request(f"{request_line}\r\nHost: ignored\r\n\r\n".encode())


def test_denied_proxy_log_never_discloses_denied_hostname() -> None:
    assert safe_log_line("metadata.google.internal", 403) == (
        "host=[DENIED] status=403"
    )


def test_proxy_limiter_paces_and_bounds_requests() -> None:
    now = [10.0]
    delays: list[float] = []

    def clock() -> float:
        return now[0]

    def sleeper(delay: float) -> None:
        delays.append(delay)
        now[0] += delay

    limiter = RequestLimiter(
        max_requests=2,
        minimum_interval_seconds=0.25,
        clock=clock,
        sleeper=sleeper,
    )
    limiter.acquire()
    now[0] += 0.1
    limiter.acquire()

    assert limiter.count == 2
    assert delays == pytest.approx([0.15])
    with pytest.raises(ProxyRateLimitExceeded):
        limiter.acquire()


def test_loads_only_repository_public_fixture() -> None:
    fixture_path = (
        Path(__file__).parents[2] / "uk_bin_collection" / "tests" / "input.json"
    )
    fixture = load_public_fixture(fixture_path)

    source = json.loads(fixture_path.read_text(encoding="utf-8"))[COUNCIL_NAME]
    assert fixture.postcode == source["postcode"]
    assert fixture.house_number == source["house_number"]
    assert fixture.url == source["url"] == PUBLIC_BINDAY_URL
    assert fixture.web_driver == source["web_driver"] == "http://selenium:4444"


def test_fixture_loader_fails_closed_on_webdriver_override(tmp_path: Path) -> None:
    fixture_path = tmp_path / "input.json"
    fixture_path.write_text(
        json.dumps(
            {
                COUNCIL_NAME: {
                    "postcode": "NG31 8XG",
                    "house_number": "43",
                    "url": PUBLIC_BINDAY_URL,
                    "web_driver": "http://host.containers.internal:4444",
                    "skip_get_url": True,
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="isolated Selenium alias"):
        load_public_fixture(fixture_path)


def test_runner_redacts_postcode_number_identifiers_and_urls() -> None:
    fixture = PublicFixture(
        postcode="NG31 8XG",
        house_number="43",
        url=PUBLIC_BINDAY_URL,
        web_driver="http://selenium:4444",
    )
    raw = (
        "postcode NG31 8XG / NG318XG number 43 "
        "UPRN=123456789012 and https://example.test/path?address=43"
    )

    redacted = redact_output(raw, fixture)

    assert "NG31" not in redacted
    assert "NG318XG" not in redacted
    assert "123456789012" not in redacted
    assert "https://" not in redacted
    assert "example.test" not in redacted
    assert " 43" not in redacted


def test_result_parser_returns_only_non_identifying_counts() -> None:
    summary = parse_collection_result(
        json.dumps(
            {
                "bins": [
                    {"type": "Grey Bin", "collectionDate": "20/07/2026"},
                    {"type": "Food Bin", "collectionDate": "20/07/2026"},
                ]
            }
        )
    )

    assert summary == {
        "status": "passed",
        "council": COUNCIL_NAME,
        "logical_lookups": 1,
        "bin_count": 2,
    }


def test_runner_invokes_exactly_once_after_minimum_delay() -> None:
    fixture = PublicFixture(
        postcode="NG31 8XG",
        house_number="43",
        url=PUBLIC_BINDAY_URL,
        web_driver="http://selenium:4444",
    )
    invocations: list[PublicFixture] = []
    delays: list[float] = []

    def invoke(value: PublicFixture) -> str:
        invocations.append(value)
        return json.dumps(
            {"bins": [{"type": "Grey Bin", "collectionDate": "20/07/2026"}]}
        )

    summary = run_canary(fixture, invoke=invoke, sleeper=delays.append)

    assert invocations == [fixture]
    assert delays == [MINIMUM_START_DELAY_SECONDS]
    assert summary["logical_lookups"] == 1


def test_runner_refuses_reduced_delay() -> None:
    fixture = PublicFixture("NG31 8XG", "43", PUBLIC_BINDAY_URL, "http://selenium:4444")

    with pytest.raises(ValueError, match="cannot be reduced"):
        run_canary(
            fixture,
            invoke=lambda _: None,
            sleeper=lambda _: None,
            minimum_delay_seconds=0,
        )
