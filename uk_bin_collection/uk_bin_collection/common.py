import calendar
import holidays
import json
import os
import pandas as pd
import re
import requests
from datetime import datetime
from dateutil.parser import parse
from enum import Enum
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException
from urllib3.exceptions import MaxRetryError

date_format = "%d/%m/%Y"
days_of_week = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


class Region(Enum):
    ENG = 1
    NIR = 2
    SCT = 3
    WLS = 4


def check_postcode(postcode: str):
    """
    Checks a postcode exists and validates UK formatting against a RegEx string
        :param postcode: Postcode to parse
    """
    postcode_api_url = "https://api.postcodes.io/postcodes/"
    postcode_api_response = requests.get(f"{postcode_api_url}{postcode}")

    if postcode_api_response.status_code != 200:
        val_error = json.loads(postcode_api_response.text)
        raise ValueError(
            f"Exception: {val_error['error']} Status: {val_error['status']}"
        )
    return True


def check_paon(paon: str):
    """
    Checks that PAON data exists
        :param paon: PAON data to check, usually house number
    """
    try:
        if paon is None:
            raise ValueError("Invalid house number")
        return True
    except Exception as ex:
        print(f"Exception encountered: {ex}")
        print("Please check the provided house number.")
        exit(1)


def check_uprn(uprn: str):
    """
    Checks that the UPRN exists
        :param uprn: UPRN to check
    """
    try:
        if uprn is None or uprn == "":
            raise ValueError("Invalid UPRN")
        return True
    except Exception as ex:
        print(f"Exception encountered: {ex}")
        print("Please check the provided UPRN.")


def check_usrn(usrn: str):
    """
    Checks that the USRN exists
        :param uprn: USRN to check
    """
    try:
        if usrn is None or usrn == "":
            raise ValueError("Invalid USRN")
        return True
    except Exception as ex:
        print(f"Exception encountered: {ex}")
        print("Please check the provided USRN.")


def get_date_with_ordinal(date_number: int) -> str:
    """
    Return ordinal text on day of date
        :rtype: str
        :param date_number: Date number as an integer (e.g. 4)
        :return: Return date with ordinal suffix (e.g. 4th)
    """
    return str(date_number) + (
        "th"
        if 4 <= date_number % 100 <= 20
        else {1: "st", 2: "nd", 3: "rd"}.get(date_number % 10, "th")
    )


def remove_ordinal_indicator_from_date_string(date_string: str) -> str:
    """
    Remove the ordinal indicator from a written date as a string.
    E.g. June 12th 2022 -> June 12 2022
    :rtype: str
    """
    ord_day_pattern = re.compile(r"(?<=\d)(st|nd|rd|th)")
    return re.compile(ord_day_pattern).sub("", date_string)


def parse_header(raw_header: str) -> dict:
    """
    Parses a header string and returns one that can be useful
            :rtype: dict
            :param raw_header: header as a string, with values to separate as pipe (|)
            :return: header in a dictionary format that can be used in requests
    """
    header = dict()
    for line in raw_header.split("|"):
        if line.startswith(":"):
            a, b = line[1:].split(":", 1)
            a = f":{a}"
        else:
            a, b = line.split(":", 1)

        header[a.strip()] = b.strip()

    return header


def is_holiday(date_to_check: datetime, region: Region = Region.ENG) -> bool:
    """
    Checks if a given date is a public holiday
        :param date_to_check: Date to check if holiday
        :param region: The UK nation to check. Defaults to ENG.
        :return: Bool - true if a holiday, false if not
    """
    uk_holidays = holidays.country_holidays("GB", subdiv=region.name)

    if date_to_check in uk_holidays:
        return True
    else:
        return False


def get_weekday_dates_in_period(start: datetime, day_of_week: int, amount=8) -> list:
    """
    Returns a list of dates of a given weekday from a start date for the given amount of weeks
        :param start: Start date
        :param day_of_week: Day of week number. Recommended to use calendar.DAY (Monday=0, Sunday=6)
        :param amount: Number of weeks to get dates. Defaults to 8 weeks.
        :return: List of dates where the specified weekday is in the period
    """
    return (
        pd.date_range(
            start=start, freq=f"W-{calendar.day_abbr[day_of_week]}", periods=amount
        )
        .strftime(date_format)
        .tolist()
    )


def get_dates_every_x_days(start: datetime, step: int, amount: int = 8) -> list:
    """
    Returns a list of dates for `X` days from start date. For example, calling `get_stepped_dates_in_period(s, 21, 4)` would
    return `4` dates every `21` days from the start date `s`
        :param start: Date to start from
        :param step: X amount of days
        :param amount: Number of dates to find
        :return: List of dates every X days from start date
        :rtype: list
    """
    return (
        pd.date_range(start=start, freq=f"{step}D", periods=amount)
        .strftime(date_format)
        .tolist()
    )


def get_next_occurrence_from_day_month(date: datetime) -> datetime:
    current_date = datetime.now()
    # Get the current day and month as integers
    current_day = current_date.day
    current_month = current_date.month

    # Extract the target day and month from the input date
    target_day = date.day
    target_month = date.month

    # Check if the target date has already occurred this year
    if (target_month < current_month) or (
        target_month == current_month and target_day < current_day
    ):
        date = pd.to_datetime(date) + pd.DateOffset(years=1)

    return date


def remove_alpha_characters(input_string: str) -> str:
    return "".join(c for c in input_string if c.isdigit() or c == " ")


def update_input_json(council: str, url: str, input_file_path: str, **kwargs):
    """
    Create or update a council's entry in the input.json file.

    :param council: Name of the council.
    :param url: URL associated with the council.
    :param input_file_path: Path to the input JSON file.
    :param kwargs: Additional parameters to store (postcode, paon, uprn, usrn, web_driver, skip_get_url).
    """
    try:
        data = load_data(input_file_path)
        council_data = data.get(council, {"wiki_name": council})
        council_data.update({"url": url, **kwargs})
        data[council] = council_data

        save_data(input_file_path, data)
    except IOError as e:
        print(f"Error updating the JSON file: {e}")
    except json.JSONDecodeError:
        print("Failed to decode JSON, check the integrity of the input file.")


def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return {}


def save_data(file_path, data):
    with open(file_path, "w") as file:
        json.dump(data, file, sort_keys=True, indent=4)


def contains_date(string, fuzzy=False) -> bool:
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False


def create_webdriver(
    web_driver: str = None,
    headless: bool = True,
    user_agent: str = None,
    session_name: str = None,
) -> webdriver.Chrome:
    """
    Create and return a Chrome WebDriver configured for optional headless operation.

    :param web_driver: URL to the Selenium server for remote web drivers. If None, a local driver is created.
    :param headless: Whether to run the browser in headless mode.
    :param user_agent: Optional custom user agent string.
    :param session_name: Optional custom session name string.
    :return: An instance of a Chrome WebDriver.
    :raises WebDriverException: If the WebDriver cannot be created.
    """
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-dev-shm-usage")
    if user_agent:
        options.add_argument(f"--user-agent={user_agent}")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    if session_name and web_driver:
        options.set_capability("se:name", session_name)

    try:
        if web_driver:
            return webdriver.Remote(command_executor=web_driver, options=options)
        else:
            return webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()), options=options
            )
    except MaxRetryError as e:
        print(f"Failed to create WebDriver: {e}")
        raise
