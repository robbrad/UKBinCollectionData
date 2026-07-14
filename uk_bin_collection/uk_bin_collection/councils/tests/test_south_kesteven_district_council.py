"""Deterministic tests for the South Kesteven browser-only checker flow."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp
from uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil import (
    CouncilClass,
)
from uk_bin_collection.uk_bin_collection.exceptions import (
    AddressMismatchError,
    BrowserUnavailableError,
    ConfigurationError,
    SiteChanged,
    UpstreamAccessDenied,
)

MODULE_PATH = (
    "uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil"
)
CHECKER_URL = (
    "https://selfservice.southkesteven.gov.uk/renderform?" "t=213&k=public-test-token"
)
BINDAY_HTML = f"""
    <html><body>
      <a href="{CHECKER_URL}"><span>Postcode bin day checker</span></a>
    </body></html>
"""
RESULTS_HTML = """
    <html><div id="body-content"><h1>Your Collections</h1>
      <table class="Alloy-table">
        <tr><td>Thursday 16 April, 2026</td><td>240 Litre Refuse</td></tr>
        <tr><td>Thursday 23 April, 2026</td><td>240 Litre Recycling</td></tr>
        <tr><td>Thursday 30 April, 2026</td><td>23lt Food Caddy</td></tr>
        <tr><td>Thursday 07 May, 2026</td><td>240 Litre Paper and Card</td></tr>
      </table>
    </div></html>
"""
UNKNOWN_RESULTS_HTML = """
    <html><div id="body-content"><h1>Your Collections</h1>
      <table class="Alloy-table">
        <tr><td>Thursday 30 April, 2026</td><td>Glass Box Collection</td></tr>
      </table>
    </div></html>
"""


class FakeTimeout(Exception):
    """Stand-in for Selenium's timeout exception."""


class FakeWebDriverError(Exception):
    """Stand-in for Selenium's WebDriver exception."""


class FakePageLoadTimeout(FakeWebDriverError):
    """Stand-in for Selenium's page-load timeout exception."""


class FakeNoSuchElement(Exception):
    """Stand-in for Selenium's missing-element exception."""


class FakeUnexpectedTagName(Exception):
    """Stand-in for Selenium's unexpected-element-type exception."""


class FakeExpectedConditions:
    """Return a callable marker without importing Selenium in this test module."""

    @staticmethod
    def element_to_be_clickable(locator):
        return lambda _driver: locator


def make_option(text: str) -> MagicMock:
    option = MagicMock()
    option.text = text
    return option


def make_support(select=None):
    wait_factory = MagicMock(
        side_effect=lambda driver, timeout: SimpleNamespace(
            _driver=driver, timeout=timeout
        )
    )
    select_factory = MagicMock(return_value=select or MagicMock(options=[]))
    return SimpleNamespace(
        By=SimpleNamespace(ID="id"),
        EC=FakeExpectedConditions,
        Select=select_factory,
        WebDriverWait=wait_factory,
        NoSuchElementException=FakeNoSuchElement,
        TimeoutException=FakeTimeout,
        UnexpectedTagNameException=FakeUnexpectedTagName,
        WebDriverException=FakeWebDriverError,
    )


@pytest.fixture
def council():
    return CouncilClass()


def test_parse_data_requires_postcode(council):
    with pytest.raises(ConfigurationError, match="Postcode is required"):
        council.parse_data("", paon="43")


def test_parse_data_requires_paon(council):
    with pytest.raises(ConfigurationError, match="Property number or name is required"):
        council.parse_data("", postcode="NG31 8XG")


def test_parse_data_requires_remote_webdriver_before_browser_creation(council):
    with patch(f"{MODULE_PATH}.create_webdriver") as create:
        with pytest.raises(ConfigurationError, match="remote Selenium WebDriver"):
            council.parse_data("", postcode="NG31 8XG", paon="43")

    create.assert_not_called()


def test_find_checker_url_extracts_only_supported_https_service(council):
    assert council._find_checker_url(BINDAY_HTML, council.BIN_DAY_URL) == CHECKER_URL

    malicious = BINDAY_HTML.replace(
        CHECKER_URL, "https://example.invalid/collect?address=secret"
    )
    with pytest.raises(SiteChanged, match="outside the supported service"):
        council._find_checker_url(malicious, council.BIN_DAY_URL)


def test_address_selection_uses_exact_normalized_paon(council):
    matching = make_option("4 Pembroke Avenue, Grantham, NG31 8XG")
    select = MagicMock(
        options=[
            make_option("43 Pembroke Avenue, Grantham, NG31 8XG"),
            matching,
        ]
    )
    support = make_support(select)

    council._select_address(MagicMock(), " 4 ", support)

    select.select_by_visible_text.assert_called_once_with(matching.text)


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        (
            [make_option("41 High Street, Grantham")],
            "was not found",
        ),
        (
            [
                make_option("The Cottage, High Street, Grantham"),
                make_option("  THE   COTTAGE , Low Street, Grantham"),
            ],
            "matched more than one",
        ),
    ],
)
def test_address_selection_rejects_missing_or_ambiguous_matches(
    council, options, expected
):
    support = make_support(MagicMock(options=options))

    with pytest.raises(AddressMismatchError, match=expected):
        council._select_address(MagicMock(), "The Cottage", support)


@pytest.mark.parametrize("operation", ["wait", "select"])
def test_address_control_tag_drift_is_typed_as_site_changed(council, operation):
    support = make_support()
    support.Select.side_effect = FakeUnexpectedTagName("Select only works on <select>")

    with pytest.raises(SiteChanged, match="no longer a selection list"):
        if operation == "wait":
            address_control = MagicMock()
            address_control.is_displayed.return_value = True
            driver = MagicMock()
            driver.find_element.return_value = address_control
            council._address_options_ready(driver, support)
        else:
            council._select_address(MagicMock(), "43", support)


def test_parse_collection_rows_parses_and_normalizes_all_bins(council):
    assert council._parse_collection_rows(RESULTS_HTML) == [
        {"type": "Black Bin", "collectionDate": "16/04/2026"},
        {"type": "Grey Bin", "collectionDate": "23/04/2026"},
        {"type": "Food Bin", "collectionDate": "30/04/2026"},
        {"type": "Purple Bin", "collectionDate": "07/05/2026"},
    ]


def test_parse_collection_rows_preserves_unknown_labels(council):
    assert council._parse_collection_rows(UNKNOWN_RESULTS_HTML) == [
        {"type": "Glass Box Collection", "collectionDate": "30/04/2026"}
    ]


def test_parse_collection_rows_classifies_missing_results_as_site_change(council):
    with pytest.raises(SiteChanged, match="No collection rows"):
        council._parse_collection_rows("<html><body>No table</body></html>")


def test_wait_timeout_is_classified_as_site_change(council):
    wait = MagicMock()
    wait.until.side_effect = FakeTimeout("delayed")
    support = make_support()

    with pytest.raises(SiteChanged, match="postcode input is missing"):
        council._wait_for_clickable(
            wait,
            support,
            (support.By.ID, council.POSTCODE_INPUT_ID),
            "The postcode input is missing from the South Kesteven checker.",
        )


@pytest.mark.parametrize(
    "wait_kind",
    ["checker", "clickable", "address_options", "address_confirmation", "results"],
)
def test_wait_timeouts_preserve_browser_access_denial(council, wait_kind):
    driver = MagicMock()
    driver.page_source = "<html><h1>403 Forbidden</h1>Access denied</html>"
    wait = MagicMock()
    wait._driver = driver
    wait.until.side_effect = FakeTimeout("blocked")
    support = make_support()

    with pytest.raises(UpstreamAccessDenied, match="denied browser access"):
        if wait_kind == "checker":
            council._wait_for_checker_url(wait, support, council.BIN_DAY_URL)
        elif wait_kind == "clickable":
            council._wait_for_clickable(
                wait,
                support,
                (support.By.ID, council.POSTCODE_INPUT_ID),
                "missing",
            )
        elif wait_kind == "address_options":
            council._wait_for_address_options(wait, support)
        elif wait_kind == "address_confirmation":
            council._wait_for_address_confirmation(wait, support)
        else:
            council._wait_for_results_container(
                wait,
                support,
                "488",
                "<div>initial form</div>",
            )


def test_checker_wait_session_loss_is_typed_as_browser_unavailable(council):
    driver = MagicMock()
    driver.page_source = BINDAY_HTML
    wait = MagicMock(_driver=driver)
    wait.until.side_effect = FakeWebDriverError("lost session")
    support = make_support()

    with patch(f"{MODULE_PATH}.create_webdriver", return_value=driver), patch.object(
        council, "_load_selenium_support", return_value=support
    ), patch.object(council, "_new_wait", return_value=wait):
        with pytest.raises(BrowserUnavailableError, match="stopped responding"):
            council.parse_data(
                "",
                postcode="NG31 8XG",
                paon="43",
                web_driver="http://selenium:4444",
            )

    driver.quit.assert_called_once_with()


def test_app_run_intrinsically_skips_generic_get_for_south_kesteven():
    """The CLI/API execution path must not rely on callers supplying a flag."""
    app = UKBinCollectionApp()
    app.set_args(
        [
            "SouthKestevenDistrictCouncil",
            CouncilClass.BIN_DAY_URL,
            "--postcode=NG31 8XG",
            "--number=43",
            "--web_driver=http://selenium:4444",
        ]
    )

    with patch(
        "uk_bin_collection.uk_bin_collection.collect_data.import_council_module",
        return_value=SimpleNamespace(CouncilClass=CouncilClass),
    ), patch.object(
        CouncilClass,
        "get_data",
        side_effect=AssertionError("generic HTTP preflight must not run"),
    ) as generic_get, patch.object(
        CouncilClass,
        "parse_data",
        autospec=True,
        return_value={"bins": []},
    ) as parse_data:
        result = json.loads(app.run())

    assert result == {"bins": []}
    generic_get.assert_not_called()
    assert parse_data.call_args.args[1] == ""
    assert parse_data.call_args.kwargs["skip_get_url"] is False
    assert parse_data.call_args.kwargs["url"] == CouncilClass.BIN_DAY_URL


def test_parse_data_uses_one_browser_session_and_never_calls_http_preflight(council):
    driver = MagicMock()
    driver.page_source = RESULTS_HTML
    postcode_input = MagicMock()
    search_button = MagicMock()
    submit_button = MagicMock()
    address_select = MagicMock()
    matching = make_option("43 Pembroke Avenue, Grantham, NG31 8XG")
    select = MagicMock(options=[matching])
    support = make_support(select)

    with patch(f"{MODULE_PATH}.create_webdriver", return_value=driver) as create, patch(
        "requests.get", side_effect=AssertionError("HTTP preflight must not run")
    ), patch.object(
        council, "_load_selenium_support", return_value=support
    ), patch.object(
        council, "_wait_for_checker_url", return_value=CHECKER_URL
    ), patch.object(
        council,
        "_wait_for_clickable",
        side_effect=[postcode_input, search_button, submit_button],
    ), patch.object(
        council, "_wait_for_address_options", return_value=address_select
    ), patch.object(
        council, "_wait_for_address_confirmation"
    ), patch.object(
        council, "_wait_for_results_container"
    ), patch.object(
        council, "_get_current_section_id", return_value="488"
    ), patch.object(
        council, "_get_body_markup", return_value="<div>Address form</div>"
    ):
        result = council.parse_data(
            "ignored preflight body",
            url="https://unreviewed.invalid/redirect",
            postcode="NG31 8XG",
            paon="43",
            web_driver="http://selenium:4444",
            user_agent="UKBCD deterministic test",
        )

    assert result["bins"][0] == {
        "type": "Black Bin",
        "collectionDate": "16/04/2026",
    }
    assert driver.get.call_args_list == [
        call(council.BIN_DAY_URL),
        call(CHECKER_URL),
    ]
    create.assert_called_once()
    assert create.call_args.args == (
        "http://selenium:4444",
        True,
        "UKBCD deterministic test",
        council.__class__.__module__,
    )
    assert 0 < create.call_args.kwargs["command_timeout"] <= 30
    postcode_input.clear.assert_called_once_with()
    postcode_input.send_keys.assert_called_once_with("NG31 8XG")
    search_button.click.assert_called_once_with()
    submit_button.click.assert_called_once_with()
    select.select_by_visible_text.assert_called_once_with(matching.text)
    driver.quit.assert_called_once_with()


def test_access_denial_after_postcode_search_is_typed_and_session_is_closed(council):
    driver = MagicMock()
    driver.page_source = BINDAY_HTML
    postcode_input = MagicMock()
    search_button = MagicMock()
    search_button.click.side_effect = lambda: setattr(
        driver,
        "page_source",
        "<html><h1>403 Forbidden</h1>Access denied</html>",
    )
    support = make_support()

    with patch(f"{MODULE_PATH}.create_webdriver", return_value=driver), patch.object(
        council, "_load_selenium_support", return_value=support
    ), patch.object(
        council, "_wait_for_checker_url", return_value=CHECKER_URL
    ), patch.object(
        council,
        "_wait_for_clickable",
        side_effect=[postcode_input, search_button],
    ), patch.object(
        council, "_get_current_section_id", return_value="488"
    ), patch.object(
        council, "_get_body_markup", return_value="<div>Address form</div>"
    ), patch.object(
        council, "_wait_for_address_options"
    ) as wait_for_addresses:
        with pytest.raises(UpstreamAccessDenied, match="denied browser access"):
            council.parse_data(
                "",
                postcode="NG31 8XG",
                paon="43",
                web_driver="http://selenium:4444",
            )

    wait_for_addresses.assert_not_called()
    driver.quit.assert_called_once_with()


def test_access_denial_after_submit_is_typed_and_session_is_closed(council):
    driver = MagicMock()
    driver.page_source = BINDAY_HTML
    postcode_input = MagicMock()
    search_button = MagicMock()
    submit_button = MagicMock()
    submit_button.click.side_effect = lambda: setattr(
        driver,
        "page_source",
        "<html><h1>403 Forbidden</h1>Access denied</html>",
    )
    address_select = MagicMock()
    matching = make_option("43 Pembroke Avenue, Grantham, NG31 8XG")
    support = make_support(MagicMock(options=[matching]))

    with patch(f"{MODULE_PATH}.create_webdriver", return_value=driver), patch.object(
        council, "_load_selenium_support", return_value=support
    ), patch.object(
        council, "_wait_for_checker_url", return_value=CHECKER_URL
    ), patch.object(
        council,
        "_wait_for_clickable",
        side_effect=[postcode_input, search_button, submit_button],
    ), patch.object(
        council, "_wait_for_address_options", return_value=address_select
    ), patch.object(
        council, "_wait_for_address_confirmation"
    ), patch.object(
        council, "_wait_for_results_container"
    ) as wait_for_results, patch.object(
        council, "_get_current_section_id", return_value="488"
    ), patch.object(
        council, "_get_body_markup", return_value="<div>Address form</div>"
    ):
        with pytest.raises(UpstreamAccessDenied, match="denied browser access"):
            council.parse_data(
                "",
                postcode="NG31 8XG",
                paon="43",
                web_driver="http://selenium:4444",
            )

    wait_for_results.assert_not_called()
    driver.quit.assert_called_once_with()


def test_browser_403_is_typed_and_session_is_closed(council):
    driver = MagicMock()
    driver.page_source = "<html><title>403 Forbidden</title>Access denied</html>"
    support = make_support()

    with patch(f"{MODULE_PATH}.create_webdriver", return_value=driver), patch.object(
        council, "_load_selenium_support", return_value=support
    ):
        with pytest.raises(UpstreamAccessDenied, match="denied browser access"):
            council.parse_data(
                "",
                postcode="NG31 8XG",
                paon="43",
                web_driver="http://selenium:4444",
            )

    driver.quit.assert_called_once_with()


def test_page_load_timeout_with_denial_preserves_access_denied(council):
    driver = MagicMock()
    driver.page_source = "<html><h1>403 Forbidden</h1>Access denied</html>"
    driver.get.side_effect = FakePageLoadTimeout("page load timed out")
    support = make_support()

    with patch(f"{MODULE_PATH}.create_webdriver", return_value=driver), patch.object(
        council, "_load_selenium_support", return_value=support
    ):
        with pytest.raises(UpstreamAccessDenied, match="denied browser access"):
            council.parse_data(
                "",
                postcode="NG31 8XG",
                paon="43",
                web_driver="http://selenium:4444",
            )

    driver.quit.assert_called_once_with()


def test_webdriver_creation_failure_is_typed(council):
    with patch(
        f"{MODULE_PATH}.create_webdriver",
        side_effect=BrowserUnavailableError("offline"),
    ):
        with pytest.raises(BrowserUnavailableError, match="offline"):
            council.parse_data(
                "",
                postcode="NG31 8XG",
                paon="43",
                web_driver="http://selenium:4444",
            )


def test_total_deadline_is_enforced_and_session_is_closed(council):
    driver = MagicMock()
    support = make_support()

    with patch(f"{MODULE_PATH}.monotonic", side_effect=[0.0, 91.0]), patch(
        f"{MODULE_PATH}.create_webdriver", return_value=driver
    ) as create, patch.object(council, "_load_selenium_support", return_value=support):
        with pytest.raises(SiteChanged, match="exceeded its total timeout"):
            council.parse_data(
                "",
                postcode="NG31 8XG",
                paon="43",
                web_driver="http://selenium:4444",
            )

    create.assert_not_called()
    driver.get.assert_not_called()
    driver.quit.assert_not_called()


def test_opt_in_artifacts_are_redacted_and_never_capture_screenshots(council, tmp_path):
    driver = MagicMock()
    driver.current_url = (
        "https://selfservice.southkesteven.gov.uk/"
        "renderform/100012345678?postcode=NG31%208XG&paon=43"
    )
    driver.page_source = (
        "<html>Postcode NG31 8XG / NG318XG / NG31%208XG; property 43; "
        '<input id="FF5265" value="100012345678" type="hidden">'
        '<select id="FF5265-list"><option value="secret" selected>'
        "43 Secret Road</option></select>"
        '<span id="FF5265-displayname">43 Codex Avenue</span>'
        '<input id="opaque-form-field" value="opaque-household-token">'
        '<div hidden data-address="Hidden Secret Lane">Hidden Secret Lane</div>'
        '<script>const selectedAddress = "Script Secret Road";</script>'
        "safe fixture content</html>"
    )

    artifact_path = council._capture_debug_artifacts(
        driver,
        tmp_path,
        stage="select_address",
        redactions=("NG31 8XG", "43"),
    )

    assert artifact_path is not None
    page = (artifact_path / "page.html").read_text(encoding="utf-8")
    metadata_text = (artifact_path / "metadata.json").read_text(encoding="utf-8")
    metadata = json.loads(metadata_text)
    combined = f"{page}\n{metadata_text}"
    assert "NG31 8XG" not in combined
    assert "NG318XG" not in combined
    assert "NG31%208XG" not in combined
    assert "100012345678" not in combined
    assert "Secret Road" not in combined
    assert "Codex Avenue" not in combined
    assert "opaque-household-token" not in combined
    assert "Hidden Secret Lane" not in combined
    assert "Script Secret Road" not in combined
    assert "selected" not in page
    assert "paon=" not in combined
    assert "safe fixture content" in page
    assert metadata == {
        "current_url": "https://selfservice.southkesteven.gov.uk",
        "stage": "select_address",
    }
    driver.save_screenshot.assert_not_called()


def test_artifact_url_preserves_only_allowlisted_origin_or_static_route(council):
    assert council._sanitize_url(CHECKER_URL) == (
        "https://selfservice.southkesteven.gov.uk/renderform"
    )
    assert (
        council._sanitize_url(
            "https://selfservice.southkesteven.gov.uk/address/100012345678"
        )
        == "https://selfservice.southkesteven.gov.uk"
    )
    assert (
        council._sanitize_url("https://example.invalid/renderform/100012345678") is None
    )


def test_artifact_write_failure_does_not_replace_original_error(council, tmp_path):
    not_a_directory = tmp_path / "artifact-root"
    not_a_directory.write_text("file", encoding="utf-8")
    driver = MagicMock()
    driver.page_source = "<html><title>403 Forbidden</title></html>"
    support = make_support()

    with patch(f"{MODULE_PATH}.create_webdriver", return_value=driver), patch.object(
        council, "_load_selenium_support", return_value=support
    ):
        with pytest.raises(UpstreamAccessDenied):
            council.parse_data(
                "",
                postcode="NG31 8XG",
                paon="43",
                web_driver="http://selenium:4444",
                artifact_dir=str(not_a_directory),
            )

    driver.quit.assert_called_once_with()
