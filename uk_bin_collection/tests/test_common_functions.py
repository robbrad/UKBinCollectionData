from uk_bin_collection.common import *
import pytest


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


def test_is_not_holiday():
    date = "20"
    result = is_holiday("2022, 12, 01")
    assert result is False


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
    assert result[6] == '27/03/2023'


def test_get_dates_every_x_days_bad():
    now = datetime(2023, 2, 25, 7, 7, 17, 748661)
    result = get_dates_every_x_days(now, 5, 7)
    assert len(result) != 8
    assert result[6] != '27/03/2022'


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
    assert result[6] == '08/04/2023'


def test_get_weekday_dates_in_period_bad():
    now = datetime(2023, 2, 25, 7, 7, 17, 748661)
    result = get_weekday_dates_in_period(now, 5, 7)
    assert len(result) != 8
    assert result[6] != '08/04/20232'
