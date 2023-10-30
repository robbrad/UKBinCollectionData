import calendar
import holidays
import json
import os
import pandas as pd
import re
import requests
from datetime import datetime
from enum import Enum
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

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
    UK = 1
    ENG = 2
    NIR = 3
    SCT = 4
    WLS = 5


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


def is_holiday(date_to_check: datetime, region: Region = Region.UK) -> bool:
    """
    Checks if a given date is a public holiday
        :param date_to_check: Date to check if holiday
        :param region: The UK nation to check. Defaults to UK.
        :return: Bool - true if a holiday, false if not
    """
    if region.name != "UK":
        subdiv = region.name.capitalize()
    else:
        subdiv = region.name

    uk_holidays = holidays.country_holidays("GB", subdiv=subdiv)

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


def get_dates_every_x_days(start: datetime, x: int, amount: int = 8) -> list:
    """
    Returns a list of dates for `X` days from start date. For example, calling `get_stepped_dates_in_period(s, 21, 4)` would
    return `4` dates every `21` days from the start date `s`
        :param start: Date to start from
        :param x: X amount of days
        :param amount: Number of dates to find
        :return: List of dates every X days from start date
        :rtype: list
    """
    return (
        pd.date_range(start=start, freq=f"{x}D", periods=amount)
        .strftime(date_format)
        .tolist()
    )


def get_next_occurrence_from_day_month(date: datetime) -> datetime:
    day = datetime.now().date().strftime("%d")
    month = datetime.now().date().strftime("%m")
    if date.strftime("%m") < month or (date.strftime("%m") == month and date.strftime("%d") < day):
        date = pd.to_datetime(date) + pd.DateOffset(years=1)
    return date


def remove_alpha_characters(input_string: str) -> str:
    return "".join(c for c in input_string if c.isdigit() or c == " ")


def write_output_json(council: str, content: str):
    cwd = os.getcwd()
    outputs_path = os.path.join(cwd, "..", "tests", "outputs")
    if not os.path.exists(outputs_path) or not os.path.isdir(outputs_path):
        outputs_path = os.path.join(cwd, "uk_bin_collection", "tests", "outputs")
    if os.path.exists(outputs_path) and os.path.isdir(outputs_path):
        with open(os.path.join(outputs_path, council + ".json"), "w") as f:
            f.write(content)
    else:
        print("Exception encountered: Unable to save Output JSON file for the council.")
        print(
            "Please check you're running developer mode from either the UKBinCollectionData "
            "or uk_bin_collection/uk_bin_collection/ directories."
        )


def validate_dates(bin_dates: dict) -> dict:
    raise NotImplementedError()
    # If a date is in December and the next is in January, increase the year


def create_webdriver() -> webdriver.Chrome:
    """
    Create and return a headless Selenium webdriver
    :rtype: webdriver.Chrome
    """
    # Set up Selenium to run 'headless'
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    # Return a Selenium webdriver
    return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
