from unittest import mock
import pytest
from uk_bin_collection.common import *
from io import StringIO
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock
from selenium import webdriver


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


def test_is_holiday():
    date = "20"
    result = is_holiday("2022, 12, 25")
    assert result is True

def test_is_holiday():
    date = "20"
    result = is_holiday("2022, 12, 25")
    assert result is True

def test_is_holiday_region():
    date = "20"
    result = is_holiday("2022, 12, 25", Region.WLS)
    assert result is True


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
    result = get_next_occurrence_from_day_month(datetime(2023,12,1))
    assert result == datetime(2023, 12, 1, 0, 0)

def test_get_next_occurrence_from_day_month_true():
    result = get_next_occurrence_from_day_month(datetime(2023,9,1))
    assert result == pd.Timestamp('2024-09-01 00:00:00')

def test_write_output_json():
    council = "test_council"
    content = '{"example": "data"}'
    write_output_json(council, content)
    cwd = os.getcwd()
    outputs_path = os.path.join(cwd, "uk_bin_collection", "tests", "outputs", council + ".json")
    result1 = os.path.exists(outputs_path)        

    with open(outputs_path, "r") as f:
        read_content = f.read()

    if os.path.exists(outputs_path):
        os.remove(outputs_path)

    assert result1 == True
    assert read_content == content

def test_write_output_json_fail(capsys, monkeypatch):
    def mock_os_path_exists(path):
        return False  # Simulate the path not existing

    monkeypatch.setattr(os.path, 'exists', mock_os_path_exists)

    council = "test_council"
    content = '{"example": "data"}'
    write_output_json(council, content)

    captured = capsys.readouterr()
    assert "Exception encountered: Unable to save Output JSON file for the council." in captured.out
    assert "Please check you're running developer mode" in captured.out

def test_create_webdriver():
    result = create_webdriver()
    assert result.name == 'chrome'
