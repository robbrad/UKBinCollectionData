"""Unit tests for the South Kesteven District Council live checker flow."""

import json
from unittest.mock import ANY, MagicMock, patch

import pytest
from selenium.webdriver.common.by import By

from uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil import (
    CouncilClass,
)

MODULE_PATH = (
    "uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil"
)
CHECKER_URL = (
    "https://selfservice.southkesteven.gov.uk/renderform?"
    "t=213&k=2074C945A63DDC0D18F1EB74DA230AC3122958B1"
)
BINDAY_HTML = f"""
    <html>
        <body>
            <a href="{CHECKER_URL}">
                <span>Postcode bin day checker</span>
            </a>
        </body>
    </html>
"""
RESULTS_HTML = """
    <html>
        <div id="body-content">
            <h1>Your Collections</h1>
            <table class="Alloy-table">
                <tr>
                    <td>Thursday 16 April, 2026</td>
                    <td>240 Litre Refuse</td>
                </tr>
                <tr>
                    <td>Thursday 23 April, 2026</td>
                    <td>240 Litre Recycling</td>
                </tr>
                <tr>
                    <td>Thursday 30 April, 2026</td>
                    <td>23lt Food Caddy</td>
                </tr>
                <tr>
                    <td>Thursday 07 May, 2026</td>
                    <td>240 Litre Paper and Card</td>
                </tr>
            </table>
        </div>
    </html>
"""
UNKNOWN_RESULTS_HTML = """
    <html>
        <div id="body-content">
            <h1>Your Collections</h1>
            <table class="Alloy-table">
                <tr>
                    <td>Thursday 30 April, 2026</td>
                    <td>Glass Box Collection</td>
                </tr>
            </table>
        </div>
    </html>
"""


@pytest.fixture
def council():
    return CouncilClass()


def make_option(text: str) -> MagicMock:
    option = MagicMock()
    option.text = text
    return option


def test_parse_data_requires_postcode(council):
    with pytest.raises(ValueError, match="Postcode is required for South Kesteven."):
        council.parse_data("", paon="43")


def test_parse_data_requires_paon(council):
    with pytest.raises(
        ValueError,
        match="Property number or name \\(paon\\) is required for South Kesteven.",
    ):
        council.parse_data("", postcode="NG31 8XG")


def test_resolve_checker_url_extracts_live_cta_link(council):
    checker_url = council._resolve_checker_url(council.BIN_DAY_URL, page=BINDAY_HTML)

    assert checker_url == CHECKER_URL


def test_address_options_ready_requires_visible_populated_dropdown(council):
    mock_driver = MagicMock()
    hidden_select = MagicMock()
    hidden_select.is_displayed.return_value = False
    mock_driver.find_element.return_value = hidden_select

    assert council._address_options_ready(mock_driver) is False

    visible_select = MagicMock()
    visible_select.is_displayed.return_value = True
    mock_driver.find_element.return_value = visible_select

    with patch(f"{MODULE_PATH}.Select") as mock_select_cls:
        mock_select_cls.return_value.options = [
            make_option("43 Pembroke Avenue, Grantham")
        ]

        assert council._address_options_ready(mock_driver) is visible_select


def test_select_address_raises_when_property_not_found(council):
    mock_select = MagicMock()
    mock_select.options = [
        make_option("41 Pembroke Avenue, Grantham, NG31 8XG"),
        make_option("45 Pembroke Avenue, Grantham, NG31 8XG"),
    ]

    with patch(f"{MODULE_PATH}.Select", return_value=mock_select):
        with pytest.raises(
            RuntimeError,
            match="Unable to find the property '99' in the address dropdown.",
        ):
            council._select_address(MagicMock(), "99")


def test_parse_collection_rows_parses_multiple_bins(council):
    result = council._parse_collection_rows(RESULTS_HTML)

    assert result == [
        {
            "type": "Black Bin",
            "collectionDate": "16/04/2026",
        },
        {
            "type": "Grey Bin",
            "collectionDate": "23/04/2026",
        },
        {
            "type": "Food Bin",
            "collectionDate": "30/04/2026",
        },
        {
            "type": "Purple Bin",
            "collectionDate": "07/05/2026",
        },
    ]


def test_parse_collection_rows_leaves_unknown_bin_labels_unchanged(council):
    result = council._parse_collection_rows(UNKNOWN_RESULTS_HTML)

    assert result == [
        {
            "type": "Glass Box Collection",
            "collectionDate": "30/04/2026",
        }
    ]


def test_capture_debug_artifacts_writes_files(council, tmp_path):
    mock_driver = MagicMock()
    mock_driver.current_url = CHECKER_URL
    mock_driver.page_source = "<html><body>debug</body></html>"
    mock_driver.save_screenshot.return_value = True

    artifact_path = council._capture_debug_artifacts(
        mock_driver,
        tmp_path,
        {"postcode": "NG31 8XG", "paon": "43"},
    )

    assert artifact_path is not None
    assert (artifact_path / "page.html").read_text(
        encoding="utf-8"
    ) == mock_driver.page_source
    metadata = json.loads((artifact_path / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["current_url"] == CHECKER_URL
    assert metadata["postcode"] == "NG31 8XG"
    assert metadata["screenshot_saved"] is True


def test_parse_data_uses_live_checker_url_and_form_ids(council):
    mock_driver = MagicMock()
    mock_driver.page_source = RESULTS_HTML

    current_section = MagicMock()
    current_section.get_attribute.return_value = "488"
    body_content = MagicMock()
    body_content.get_attribute.return_value = "<div>Collection Address</div>"

    def find_element_side_effect(by, value):
        if (by, value) == (By.ID, council.CURRENT_SECTION_ID):
            return current_section
        if (by, value) == (By.ID, council.BODY_CONTENT_ID):
            return body_content
        raise AssertionError(f"Unexpected find_element lookup: {(by, value)}")

    mock_driver.find_element.side_effect = find_element_side_effect

    postcode_input = MagicMock()
    search_button = MagicMock()
    submit_button = MagicMock()
    address_select = MagicMock()

    matched_option = make_option("43 Pembroke Avenue, Grantham, NG31 8XG")
    mock_select = MagicMock()
    mock_select.options = [
        make_option("41 Pembroke Avenue, Grantham, NG31 8XG"),
        matched_option,
    ]

    with patch(f"{MODULE_PATH}.create_webdriver", return_value=mock_driver), patch(
        f"{MODULE_PATH}.WebDriverWait", return_value=MagicMock()
    ), patch.object(
        council, "_resolve_checker_url", return_value=CHECKER_URL
    ), patch.object(
        council,
        "_wait_for_clickable",
        side_effect=[postcode_input, search_button, submit_button],
    ) as wait_clickable, patch.object(
        council, "_wait_for_address_options", return_value=address_select
    ) as wait_for_address, patch.object(
        council, "_wait_for_address_confirmation"
    ) as wait_for_confirmation, patch.object(
        council, "_wait_for_results_container"
    ) as wait_for_results, patch(
        f"{MODULE_PATH}.Select", return_value=mock_select
    ):
        result = council.parse_data("", postcode="NG31 8XG", paon="43")

    assert result["bins"][0]["type"] == "Black Bin"
    assert result["bins"][0]["collectionDate"] == "16/04/2026"
    mock_driver.get.assert_called_once_with(CHECKER_URL)
    postcode_input.clear.assert_called_once()
    postcode_input.send_keys.assert_called_once_with("NG31 8XG")
    search_button.click.assert_called_once()
    submit_button.click.assert_called_once()
    wait_clickable.assert_any_call(
        ANY,
        (By.ID, council.POSTCODE_INPUT_ID),
        "Unable to find the postcode input on the South Kesteven checker.",
    )
    wait_clickable.assert_any_call(
        ANY,
        (By.ID, council.SUBMIT_BUTTON_ID),
        "Unable to find the submit button after selecting the address.",
    )
    wait_for_address.assert_called_once()
    wait_for_confirmation.assert_called_once()
    wait_for_results.assert_called_once_with(
        ANY,
        "488",
        "<div>Collection Address</div>",
    )
    mock_select.select_by_visible_text.assert_called_once_with(matched_option.text)
    mock_driver.quit.assert_called_once()


def test_parse_data_appends_artifact_path_on_failure(council, tmp_path):
    mock_driver = MagicMock()
    mock_driver.current_url = CHECKER_URL
    mock_driver.page_source = "<html><body>lookup failed</body></html>"
    mock_driver.save_screenshot.return_value = True

    current_section = MagicMock()
    current_section.get_attribute.return_value = "488"
    body_content = MagicMock()
    body_content.get_attribute.return_value = "<div>Collection Address</div>"

    def find_element_side_effect(by, value):
        if (by, value) == (By.ID, council.CURRENT_SECTION_ID):
            return current_section
        if (by, value) == (By.ID, council.BODY_CONTENT_ID):
            return body_content
        raise AssertionError(f"Unexpected find_element lookup: {(by, value)}")

    mock_driver.find_element.side_effect = find_element_side_effect

    postcode_input = MagicMock()
    search_button = MagicMock()

    with patch(f"{MODULE_PATH}.create_webdriver", return_value=mock_driver), patch(
        f"{MODULE_PATH}.WebDriverWait", return_value=MagicMock()
    ), patch.object(
        council, "_resolve_checker_url", return_value=CHECKER_URL
    ), patch.object(
        council,
        "_wait_for_clickable",
        side_effect=[postcode_input, search_button],
    ), patch.object(
        council,
        "_wait_for_address_options",
        side_effect=RuntimeError(
            "Unable to find the address dropdown after searching for the postcode."
        ),
    ):
        with pytest.raises(
            RuntimeError,
            match="Unable to find the address dropdown after searching for the postcode.",
        ) as exc_info:
            council.parse_data(
                "",
                postcode="NG31 8XG",
                paon="43",
                artifact_dir=str(tmp_path),
            )

    assert "Debug artifacts saved to:" in str(exc_info.value)
    created_artifacts = list(tmp_path.iterdir())
    assert created_artifacts
    artifact_run_dir = next(path for path in created_artifacts if path.is_dir())
    assert (artifact_run_dir / "page.html").exists()
    assert (artifact_run_dir / "metadata.json").exists()
    mock_driver.quit.assert_called_once()
