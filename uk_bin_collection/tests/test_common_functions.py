from unittest import mock
import pytest
from uk_bin_collection.common import *
from io import StringIO
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock, mock_open
from selenium.common.exceptions import WebDriverException
from urllib3.exceptions import MaxRetryError


def test_check_postcode_valid():
    valid_postcode = "SW1A 1AA"
    result = check_postcode(valid_postcode)
    assert result is True


def test_check_postcode_invalid():
    invalid_postcode = "BADPOSTCODE"
    with pytest.raises(ValueError) as exc_info:
        result = check_postcode(invalid_postcode)
    assert exc_info._excinfo[1].args[0] == "Exception: Invalid postcode Status: 404"
    assert exc_info.type == ValueError


def test_check_paon():
    valid_house_num = "1"
    result = check_paon(valid_house_num)
    assert result is True


def test_check_paon_invalid(capfd):
    invalid_house_num = None
    with pytest.raises(SystemExit) as exc_info:
        result = check_paon(invalid_house_num)
    out, err = capfd.readouterr()
    assert out.startswith("Exception encountered: Invalid house number")
    assert exc_info.type == SystemExit
    assert exc_info.value.code == 1


def test_get_data_check_uprn():
    uprn = "1"
    result = check_uprn(uprn)
    assert result is True


def test_get_data_check_uprn_exception(capfd):
    uprn = None
    result = check_uprn(uprn)
    out, err = capfd.readouterr()
    assert out.startswith("Exception encountered: ")


def test_get_data_check_usrn():
    usrn = "1"
    result = check_usrn(usrn)
    assert result is True


def test_get_data_check_usrn_exception(capfd):
    usrn = None
    result = check_usrn(usrn)
    out, err = capfd.readouterr()
    assert out.startswith("Exception encountered: ")


def test_get_date_with_ordinal():
    date_number = 1
    result = get_date_with_ordinal(date_number)
    assert result == "1st"


def test_get_date_with_ordinal_exception():
    date_number = "a"
    with pytest.raises(TypeError) as exc_info:
        result = get_date_with_ordinal(date_number)
    assert exc_info.type == TypeError
    assert (
        exc_info.value.args[0] == "not all arguments converted during string formatting"
    )


def test_parse_header():
    input_header = "i:am|:a:test:header|value:test"
    result = parse_header(input_header)
    assert result == {"i": "am", ":a": "test:header", "value": "test"}
    assert type(result) is dict


# Mock data for holidays
mock_holidays = {
    datetime(2023, 1, 1): "New Year's Day",
    datetime(2023, 12, 25): "Christmas Day",
    datetime(2023, 12, 26): "Boxing Day",
}


@patch("holidays.country_holidays")
def test_is_holiday_when_true(mock_holidays_func):
    # Setting up the mock to return specific holidays
    mock_holidays_func.return_value = mock_holidays

    # Christmas Day is a holiday
    assert is_holiday(datetime(2023, 12, 25), Region.ENG) is True


@patch("holidays.country_holidays")
def test_is_holiday_when_false(mock_holidays_func):
    # Setting up the mock to return specific holidays
    mock_holidays_func.return_value = mock_holidays

    # January 2nd is not a holiday
    assert is_holiday(datetime(2023, 1, 2), Region.ENG) is False


def holiday_effect(country_code, subdiv=None):
    if subdiv == "ENG":
        return {
            datetime(2023, 12, 25): "Christmas Day",
            datetime(2023, 12, 26): "Boxing Day",
        }
    elif subdiv == "SCT":
        return {datetime(2023, 11, 30): "St Andrew's Day"}
    return {}


@patch("holidays.country_holidays", side_effect=holiday_effect)
def test_is_holiday_different_region(mock_holidays_func):
    # St Andrew's Day in Scotland
    assert is_holiday(datetime(2023, 11, 30), Region.SCT) is True

    # St Andrew's Day is not observed in England
    assert is_holiday(datetime(2023, 11, 30), Region.ENG) is False


def test_remove_alpha_characters():
    test_string = "12345abc12345"
    result = remove_alpha_characters(test_string)
    assert result == "1234512345"


def test_remove_alpha_characters_bad():
    test_string = "12345abc12345"
    result = remove_alpha_characters(test_string)
    assert result != "12345abc12345"


def test_get_dates_every_x_days():
    now = datetime(2023, 2, 25, 7, 7, 17, 748661)
    result = get_dates_every_x_days(now, 5, 7)
    assert len(result) == 7
    assert result[6] == "27/03/2023"


def test_get_dates_every_x_days_bad():
    now = datetime(2023, 2, 25, 7, 7, 17, 748661)
    result = get_dates_every_x_days(now, 5, 7)
    assert len(result) != 8
    assert result[6] != "27/03/2022"


def test_remove_ordinal_indicator_from_date_string():
    test_string = "June 12th 2022"
    result = remove_ordinal_indicator_from_date_string(test_string)
    assert result == "June 12 2022"


def test_remove_ordinal_indicator_from_date_string_bad():
    test_string = "June 12th 2022"
    result = remove_ordinal_indicator_from_date_string(test_string)
    assert result != "June 12th 2022"


def test_get_weekday_dates_in_period():
    now = datetime(2023, 2, 25, 7, 7, 17, 748661)
    result = get_weekday_dates_in_period(now, 5, 7)
    assert len(result) == 7
    assert result[6] == "08/04/2023"


def test_get_weekday_dates_in_period_bad():
    now = datetime(2023, 2, 25, 7, 7, 17, 748661)
    result = get_weekday_dates_in_period(now, 5, 7)
    assert len(result) != 8
    assert result[6] != "08/04/20232"


def test_get_next_occurrence_from_day_month_false():
    result = get_next_occurrence_from_day_month(datetime(2023, 12, 1))
    assert result == datetime(2023, 12, 1, 0, 0)


def test_get_next_occurrence_from_day_month_true():
    result = get_next_occurrence_from_day_month(datetime(2023, 1, 1))
    assert result == pd.Timestamp("2024-01-01 00:00:00")


@patch("uk_bin_collection.common.load_data", return_value={})
@patch("uk_bin_collection.common.save_data")
def test_update_input_json(mock_save_data, mock_load_data):
    update_input_json(
        "test_council",
        "TEST_URL",
        "path/to/input.json",
        postcode="TEST_POSTCODE",
        uprn="TEST_UPRN",
        web_driver="TEST_WEBDRIVER",
        skip_get_url=True,
    )
    # Check that save_data was called with expected data
    expected_data = {
        "test_council": {
            "wiki_name": "test_council",
            "url": "TEST_URL",
            "postcode": "TEST_POSTCODE",
            "uprn": "TEST_UPRN",
            "web_driver": "TEST_WEBDRIVER",
            "skip_get_url": True,
        }
    }
    mock_save_data.assert_called_once_with("path/to/input.json", expected_data)


@patch("uk_bin_collection.common.load_data")
@patch("uk_bin_collection.common.save_data")
def test_update_input_json_ioerror(mock_save_data, mock_load_data):
    mock_load_data.side_effect = IOError("Unable to access file")

    with patch("builtins.print") as mock_print:
        update_input_json("test_council", "TEST_URL", "path/to/input.json")
        mock_print.assert_called_once_with(
            "Error updating the JSON file: Unable to access file"
        )


@patch("uk_bin_collection.common.load_data")
@patch("uk_bin_collection.common.save_data")
def test_update_input_json_jsondecodeerror(mock_save_data, mock_load_data):
    mock_load_data.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)

    with patch("builtins.print") as mock_print:
        update_input_json("test_council", "TEST_URL", "path/to/input.json")
        mock_print.assert_called_once_with(
            "Failed to decode JSON, check the integrity of the input file."
        )


def test_load_data_existing_file():
    # Create a mock file with JSON content
    mock_file_data = json.dumps({"key": "value"})
    # Set up the mock to return a readable stream
    m = mock_open(read_data=mock_file_data)
    with patch("builtins.open", m):
        with patch("os.path.exists", return_value=True):
            data = load_data("path/to/mock/file.json")
            assert data == {
                "key": "value"
            }, f"Data was {data} instead of {{'key': 'value'}}"


def test_load_data_non_existing_file():
    # Simulate file not existing
    with patch("os.path.exists", return_value=False):
        data = load_data("path/to/nonexistent/file.json")
        assert data == {}


def test_load_data_invalid_json():
    # Create a mock file with invalid JSON content
    mock_file_data = '{"key": "value"'
    with patch("builtins.open", mock_open(read_data=mock_file_data)), patch(
        "json.load", side_effect=json.JSONDecodeError("Expecting ',' delimiter", "", 0)
    ):
        data = load_data("path/to/invalid.json")
        assert data == {}  # Modify based on your desired behavior


def test_save_data_to_file():
    # Mock the open function and simulate writing
    mock_file = mock_open()
    with patch("builtins.open", mock_file):
        data = {"key": "value"}
        save_data("path/to/mock/file.json", data)
        # Ensure the mock was called correctly to open the file for writing
        mock_file.assert_called_once_with("path/to/mock/file.json", "w")

        # Now check what was written to the file
        written_data = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        expected_data = json.dumps(data, sort_keys=True, indent=4)
        assert (
            written_data == expected_data
        ), "Data written to file does not match expected JSON data"


def test_save_data_io_error():
    # Simulate an IOError
    with patch("builtins.open", mock_open()) as mocked_file:
        mocked_file.side_effect = IOError("Failed to write to file")
        with pytest.raises(IOError):
            save_data("path/to/mock/file.json", {"key": "value"})


def test_contains_date_with_valid_dates():
    assert contains_date("2023-05-10")
    assert contains_date("10th of December, 2021")
    assert contains_date("March 15, 2020")
    assert contains_date("01/31/2020")


def test_contains_date_with_invalid_dates():
    assert not contains_date("not a date")
    assert not contains_date("12345")
    assert not contains_date("May 35, 2020")  # Invalid day
    assert not contains_date("2020-02-30")  # Invalid date


def test_contains_date_with_fuzzy_true():
    assert contains_date("Today is 13th of April, 2024", fuzzy=True)
    assert contains_date("They met on June 20th last year", fuzzy=True)


def test_contains_date_with_fuzzy_false():
    assert not contains_date("Today is 13th of April, 2024", fuzzy=False)
    assert not contains_date("They met on June 20th last year", fuzzy=False)


def test_contains_date_with_mixed_content():
    assert contains_date("Event starts on 2023-05-10 at 10:00 AM", fuzzy=True)
    assert not contains_date("Event starts on 2023-05-10 at 10:00 AM", fuzzy=False)


def test_create_webdriver_local():
    result = create_webdriver(None, headless=True, user_agent="FireFox")
    assert result.name in  ["chrome","chrome-headless-shell"]


def test_create_webdriver_remote_failure():
    # Test the scenario where the remote server is not available
    with pytest.raises(MaxRetryError) as exc_info:
        create_webdriver("http://invalid-url:4444", False)
