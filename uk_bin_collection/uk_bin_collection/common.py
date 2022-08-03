import re

date_format = "%d/%m/%Y"

def check_postcode(postcode: str):
    """
Checks a postcode exists and validates UK formatting against a RegEx string
    :param postcode: Postcode to parse
    """
    postcode_re = "^([A-Za-z][A-Ha-hJ-Yj-y]?[0-9][A-Za-z0-9]? ?[0-9][A-Za-z]{2}|[Gg][Ii][Rr] ?0[Aa]{2})$"
    try:
        if postcode is None or not re.fullmatch(postcode_re, postcode):
            raise ValueError("Invalid postcode")
    except Exception as ex:
        print(f"Exception encountered: {ex}")
        print(
            "Please check the provided postcode. If this error continues, please first trying setting the "
            "postcode manually on line 24 before raising an issue."
        )
        exit(1)


def check_paon(paon: str):
    """
Checks that PAON data exists
    :param paon: PAON data to check, usually house number
    """
    try:
        if paon is None:
            raise ValueError("Invalid house number")
    except Exception as ex:
        print(f"Exception encountered: {ex}")
        print(
            "Please check the provided house number. If this error continues, please first trying setting the "
            "house number manually on line 25 before raising an issue."
        )
        exit(1)


def get_date_with_ordinal(date_number: int) -> str:
    """

    :rtype: str
    :param date_number: Date number as an integer (e.g. 4)
    :return: Return date with ordinal suffix (e.g. 4th)
    """
    return str(date_number) + (
        "th" if 4 <= date_number % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(date_number % 10, "th")
    )
