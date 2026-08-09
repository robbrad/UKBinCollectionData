import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:

        bindata = {"bins": []}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }

        soup = BeautifulSoup(page.content, features="html.parser")
        button = soup.find(
            "a",
            text="Find out which bin will be collected when and sign up for a free email reminder.",
        )

        if button and button.get("href"):
            URI = button["href"]
            # Make the GET request
            response = requests.get(URI, headers=headers)
            soup = BeautifulSoup(response.content, features="html.parser")
            divs = soup.find_all("div", {"class": "editor"})
            for div in divs:
                for table in div.find_all("table"):
                    heading = table.find_previous_sibling("h2")
                    if not heading:
                        raise ValueError(
                            "Coventry bin calendar: found a schedule table with "
                            "no preceding month/year heading — page structure "
                            "may have changed"
                        )
                    year = heading.get_text(strip=True).split()[-1]

                    thead = table.find("thead")
                    tbody = table.find("tbody")
                    if not thead or not tbody:
                        raise ValueError(
                            "Coventry bin calendar: schedule table is missing "
                            "a thead/tbody — page structure may have changed"
                        )

                    bin_types = [
                        re.sub(
                            r"\s*\(.*?\)$",
                            "",
                            th.get_text(separator=" ", strip=True),
                        )
                        for th in thead.find_all("th")[1:]
                    ]

                    for row in tbody.find_all("tr"):
                        cells = row.find_all("td")
                        if len(cells) != len(bin_types) + 1:
                            raise ValueError(
                                f"Coventry bin calendar: expected 1 date cell "
                                f"plus {len(bin_types)} bin cells, found "
                                f"{len(cells)} — page structure may have changed"
                            )
                        date_text = cells[0].get_text(strip=True)
                        collection_date = datetime.strptime(
                            f"{date_text} {year}",
                            "%A %d %B %Y",
                        )
                        for bin_type, cell in zip(
                            bin_types, cells[1:], strict=True
                        ):
                            if cell.get_text(strip=True).lower() == "yes":
                                bindata["bins"].append(
                                    {
                                        "type": bin_type,
                                        "collectionDate": collection_date.strftime(
                                            date_format
                                        ),
                                    }
                                )
        else:
            print("Failed to find bin schedule")

        return bindata
