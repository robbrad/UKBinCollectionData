import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# Module-level constant so the month list is defined once and never duplicated.
_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Lines between collections that should always be skipped (never a bin type)
_SKIP_LINES = {
    "Collections may change during public holidays.",
    "Print calendar",
    "Add to iCalendar",
    "Please make sure you have your bins ready for collection.",
    "Change",
    "Next collection:",
    "Selected address:",
    "Collection calendar:",
    "to",
}


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
        # Find calendar year and month range from the "Collection calendar:"
        # heading, which is followed by:
        #   <start month> / "to" / <end month> / <4-digit year>
        # ------------------------------------------------------------------ #
        calendar_year = None
        start_month_num = None
        end_month_num = None

        for i, line in enumerate(lines):
            if line.strip().startswith("Collection calendar"):
                for j in range(i + 1, min(i + 8, len(lines))):
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

        # ------------------------------------------------------------------ #
        # Page structure per collection entry (confirmed from live page):
        #
        #   <day number>          e.g. "11"
        #   <display bin type>    e.g. "Recycling"  or "Domestic Waste"
        #   <subtype / colour>    e.g. "Recycling"  or "Refuse" or "Green"
        #
        # Multiple collections on the same day appear as separate triplets.
        # We always skip exactly the subtype line after reading the bin type.
        #
        # We use the DISPLAY bin type (e.g. "Domestic Waste", "Recycling",
        # "Green Waste") as the sensor name, not the subtype/colour.
        # ------------------------------------------------------------------ #
        current_month = None
        current_year = calendar_year
        i = 0

        # Fast-forward past the header block (everything before the first
        # month that appears AFTER the "Collection calendar:" line)
        cal_header_seen = False
        for idx, line in enumerate(lines):
            if line.startswith("Collection calendar"):
                cal_header_seen = True
            if cal_header_seen and line in _MONTH_NAMES:
                # First month in header — skip past the year line too
                # then start the main loop from the NEXT month occurrence
                for j in range(idx + 1, min(idx + 4, len(lines))):
                    if lines[j].isdigit() and len(lines[j]) == 4:
                        i = j + 1  # start after the year
                        break
                break

        while i < len(lines):
            line = lines[i]

            # Skip known non-data lines
            if line in _SKIP_LINES or (line.isdigit() and len(line) == 4):
                i += 1
                continue

            # Month heading
            if line in _MONTH_NAMES:
                month_num = _MONTH_NAMES.index(line) + 1
                if is_same_year:
                    current_year = calendar_year
                else:
                    current_year = (
                        calendar_year - 1
                        if month_num >= start_month_num
                        else calendar_year
                    )
                current_month = line
                i += 1
                continue

            # Day number — must have a current month context
            if line.isdigit() and 1 <= int(line) <= 31 and current_month:
                day = line

                # Next line must exist and be a bin type (not a digit, not a month)
                if (
                    i + 1 < len(lines)
                    and not lines[i + 1].isdigit()
                    and lines[i + 1] not in _MONTH_NAMES
                    and lines[i + 1] not in _SKIP_LINES
                ):
                    bin_type = lines[i + 1]

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

                    # Always advance past: day + bin_type + subtype = 3 lines
                    # (subtype/colour line is always present per live page structure)
                    i += 3
                    continue

            i += 1

        # Sort by collection date
        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )
        return bindata
