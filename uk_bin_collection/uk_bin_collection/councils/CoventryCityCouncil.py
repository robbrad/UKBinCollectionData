import re

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

MONTH_YEAR = re.compile(r"([A-Za-z]+)\s+(\d{4})")


class CouncilClass(AbstractGetBinDataClass):
    """
    Coventry publishes one calendar page per collection round, e.g.
    https://www.coventry.gov.uk/ThursAfwMonbincollectioncalendar
    Users find theirs via the "Find your collection day by postcode" lookup
    at https://www.coventry.gov.uk/bin-collection-calendar.

    Each page has a table per month, under a "<Month> <Year>" heading, with a
    row per collection date and a Yes/No column per bin type.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        bindata = {"bins": []}
        soup = BeautifulSoup(page.content, features="html.parser")

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue

            headers = [
                " ".join(cell.get_text().split())
                for cell in rows[0].find_all(["th", "td"])
            ]
            if not headers or "date" not in headers[0].lower():
                continue

            # The year comes from the month heading above the table
            heading = table.find_previous(["h2", "h3"])
            match = MONTH_YEAR.search(heading.get_text()) if heading else None
            if not match:
                continue
            year = int(match.group(2))

            for row in rows[1:]:
                cells = [
                    " ".join(cell.get_text().split())
                    for cell in row.find_all(["th", "td"])
                ]
                if len(cells) != len(headers):
                    continue

                # Skip rows that aren't a plain date (notes, footnotes etc.)
                # rather than losing the whole calendar
                try:
                    collection_date = datetime.strptime(
                        remove_ordinal_indicator_from_date_string(
                            f"{cells[0]} {year}"
                        ),
                        "%A %d %B %Y",
                    )
                except ValueError:
                    continue

                for bin_type, collected in zip(headers[1:], cells[1:]):
                    if collected.lower() == "yes":
                        bindata["bins"].append(
                            {
                                "type": bin_type,
                                "collectionDate": collection_date.strftime(
                                    date_format
                                ),
                            }
                        )

        if not bindata["bins"]:
            raise ValueError(
                "No collection dates found - check the URL is your bin "
                "collection calendar page from coventry.gov.uk/bin-collection-calendar"
            )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )
        return bindata
