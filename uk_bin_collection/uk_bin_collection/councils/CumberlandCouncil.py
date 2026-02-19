import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# Module-level constant so the month list is defined once and never duplicated.
_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        # Direct URL to the bin collection schedule using UPRN
        url = (
            f"https://www.cumberland.gov.uk/bins-recycling-and-street-cleaning/"
            f"waste-collections/bin-collection-schedule/view/{user_uprn}"
        )

        # Fetch the page
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Find the content region
        content_region = soup.find("div", class_="lgd-region--content")
        if not content_region:
            return bindata

        # Parse the text content to extract collection dates
        text_content = content_region.get_text()
        lines = [line.strip() for line in text_content.split("\n") if line.strip()]

        # ------------------------------------------------------------------ #
        # The heading is split across multiple lines, e.g.:
        #   "Collection calendar:"
        #   "February"
        #   "to"
        #   "August"
        #   "2026"
        #
        # We find "Collection calendar:" then scan the following lines to
        # extract the start month, end month, and year.
        #
        # For same-year calendars (start month <= end month, e.g. Feb-Aug 2026)
        # every month gets calendar_year.
        #
        # For cross-year calendars (start month > end month, e.g. Nov-Mar 2026)
        # months >= start_month_num get (calendar_year - 1) and months
        # < start_month_num get calendar_year.
        # ------------------------------------------------------------------ #
        calendar_year = None
        start_month_num = None
        end_month_num = None

        for i, line in enumerate(lines):
            if line.strip().startswith("Collection calendar"):
                for j in range(i + 1, min(i + 6, len(lines))):
                    if lines[j] in _MONTH_NAMES:
                        if start_month_num is None:
                            start_month_num = _MONTH_NAMES.index(lines[j]) + 1
                        else:
                            end_month_num = _MONTH_NAMES.index(lines[j]) + 1
                    if lines[j].isdigit() and len(lines[j]) == 4:
                        calendar_year = int(lines[j])
                break

        if calendar_year is None:
            raise ValueError(
                "Could not determine collection year from 'Collection calendar' heading. "
                "Page format may have changed."
            )

        is_same_year = (
            start_month_num is None
            or end_month_num is None
            or end_month_num >= start_month_num
        )

        current_month = None
        current_year = calendar_year
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this is a month name
            if line in _MONTH_NAMES:
                month_num = datetime.strptime(line, "%B").month

                if is_same_year:
                    current_year = calendar_year
                else:
                    # Cross-year: months on or after the start month belong to
                    # the year before the heading year
                    current_year = (
                        calendar_year - 1
                        if month_num >= start_month_num
                        else calendar_year
                    )

                current_month = line
                i += 1
                continue

            # Check if this is a day number (1-31)
            if line.isdigit() and 1 <= int(line) <= 31 and current_month:
                day = line

                if i + 1 < len(lines):
                    bin_type = lines[i + 1]

                    # Skip the subtype line (e.g. Paper, Recycling, Refuse, Green).
                    # A subtype is any line that is neither a digit nor a month name.
                    if (
                        i + 2 < len(lines)
                        and not lines[i + 2].isdigit()
                        and lines[i + 2] not in _MONTH_NAMES
                    ):
                        i += 1

                    # Parse the date
                    try:
                        date_str = f"{day} {current_month} {current_year}"
                        collection_date = datetime.strptime(date_str, "%d %B %Y")

                        dict_data = {
                            "type": bin_type,
                            "collectionDate": collection_date.strftime(date_format),
                        }
                        bindata["bins"].append(dict_data)
                    except ValueError:
                        pass

                    i += 2
                    continue

            i += 1

        # Sort by collection date
        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )
        return bindata
