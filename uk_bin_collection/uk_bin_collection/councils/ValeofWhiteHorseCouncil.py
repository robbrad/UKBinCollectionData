import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def week_has_bank_holiday(collection_date) -> bool:
    """True if an English bank holiday falls Monday to Friday of that week.

    A bank holiday shifts every collection in its week, not just the day
    itself, so the whole working week is checked.
    """
    monday = collection_date - timedelta(days=collection_date.weekday())
    return any(
        is_holiday(
            datetime.combine(monday + timedelta(days=offset), datetime.min.time())
        )
        for offset in range(5)
    )


def in_christmas_period(collection_date) -> bool:
    """True from 24 December to 17 January, when collections run late for
    weeks after the last bank holiday.

    The council's 2026/27 leaflet revises every collection from 25 December
    to 15 January (two days late until 9 January, one day late the week
    after), and 2025/26 returned to normal on 12 January. No bank holiday
    falls in those January weeks, so the week check alone does not see them.
    """
    return (collection_date.month == 12 and collection_date.day >= 24) or (
        collection_date.month == 1 and collection_date.day <= 17
    )


def collections_are_rescheduled(collection_date) -> bool:
    """True if the council will not collect on the usual day around this date."""
    return week_has_bank_holiday(collection_date) or in_christmas_period(
        collection_date
    )


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        # UPRN is passed in via a cookie. Set cookies/params and GET the page
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.7",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Referer": "https://eform.whitehorsedc.gov.uk/ebase/BINZONE_DESKTOP.eb?SOVA_TAG=VALE&ebd=0&ebz=1_1704201201813",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        }
        params = {
            "SOVA_TAG": "VALE",
            "ebd": "0",
        }
        requests.packages.urllib3.disable_warnings()
        # Azure App Gateway intermittently returns 403 on direct requests.
        # Establishing a JSESSIONID by visiting the page first (without the
        # SVBINZONE cookie) avoids this.
        session = requests.Session()
        session.headers.update(headers)
        session.get(
            "https://eform.whitehorsedc.gov.uk/ebase/BINZONE_DESKTOP.eb?SOVA_TAG=VALE&ebd=0&ebz=1_1780529431339",
            verify=False,
            timeout=15,
        )
        session.cookies.set("SVBINZONE", f"VALE%3AUPRN%40{user_uprn}")
        response = session.get(
            "https://eform.whitehorsedc.gov.uk/ebase/BINZONE_DESKTOP.eb",
            params=params,
            headers=headers,
            verify=False,
            timeout=15,
        )

        # Parse response text for super speedy finding
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        today = datetime.now().date()

        # Page has slider info side by side, which are two instances of this class
        for bin in soup.find_all("div", {"class": "bintxt"}):
            try:
                # Check bin type heading and make that bin type
                bin_type_info = list(bin.stripped_strings)
                if "rubbish" in bin_type_info[0]:
                    bin_type = "Rubbish"
                elif "recycling" in bin_type_info[0]:
                    bin_type = "Recycling"
                else:
                    raise ValueError(f"No bin info found in {bin_type_info[0]}")

                bin_date_info = list(
                    bin.find_next("div", {"class": "binextra"}).stripped_strings
                )
                # On standard collection schedule, date will be contained in the first string
                if contains_date(bin_date_info[0]):
                    raw_date = bin_date_info[0]
                # On exceptional collection schedule (e.g. around English Bank Holidays), date will be contained in the second stripped string
                else:
                    raw_date = bin_date_info[1]

                bin_date = datetime.strptime(
                    f"{raw_date} {today.year}", "%A %d %B - %Y"
                ).date()
            except Exception as ex:
                raise ValueError(f"Error parsing bin data: {ex}")

            # The page carries no year. In early January it still shows the
            # December date of the current fortnight, which read as this
            # year's December is eleven months away; a date that far ahead
            # is last year's.
            if bin_date - today > timedelta(days=180):
                bin_date = bin_date.replace(year=bin_date.year - 1)

            # The page publishes the current fortnight's pair rather than the
            # next occurrence of each bin, so a bin collected earlier in this
            # fortnight parses to a date already in the past - roll it
            # forward by the fortnightly cycle (day-based, so it naturally
            # crosses a year boundary too) until it's genuinely upcoming.
            #
            # Unless that lands where the council collects on a different
            # day, which only the page knows: leave the bin out until the
            # page catches up rather than publish a guess. Only where the
            # date lands matters: a holiday shifts the collections of its
            # own week and the fortnight then resumes on the usual day, so
            # rolling through a holiday week to a later date is fine.
            if bin_date < today:
                while bin_date < today:
                    bin_date += timedelta(days=14)
                if collections_are_rescheduled(bin_date):
                    continue

            # Build data dict for each entry
            dict_data = {
                "type": bin_type,
                "collectionDate": bin_date.strftime(date_format),
            }
            data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
