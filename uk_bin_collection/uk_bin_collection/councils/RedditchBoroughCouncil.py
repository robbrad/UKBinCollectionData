import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

ADDRESS_SEARCH_URL = "https://bincollections.redditchbc.gov.uk/"


def match_address(options, paon):
    """Pick the option whose label starts with (or contains) the house number/name.

    options: list of (value, label). Prefers "<paon> <street>" over "<paon> <flat>",
    then any whole-word occurrence. Raises ValueError if nothing matches.
    """
    paon = str(paon).strip()
    p = re.escape(paon)
    for pattern in (rf"^{p}[\s,]+[A-Za-z]", rf"^{p}[\s,]", rf"(^|[\s,]){p}([\s,]|$)"):
        for value, label in options:
            if re.search(pattern, label.strip(), re.I):
                return value
    raise ValueError(f"No address matching '{paon}' found for this postcode")


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def find_uprn(self, postcode, paon):
        """Resolve a UPRN from postcode + house number via the council's address search."""
        response = requests.post(ADDRESS_SEARCH_URL, data={"PostCode": postcode}, timeout=30)
        response.raise_for_status()
        dropdown = BeautifulSoup(response.content, "html.parser").find(
            "select", {"name": "UPRN"}
        )
        options = [
            (o.get("value"), o.get_text(strip=True))
            for o in (dropdown.find_all("option") if dropdown else [])
            if o.get("value")
        ]
        if not options:
            raise ValueError(f"No addresses found for postcode {postcode}")
        return match_address(options, paon)

    def parse_data(self, page: str, **kwargs) -> dict:

        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon") or kwargs.get("house_number")
        if not user_uprn and user_postcode and user_paon:
            user_uprn = self.find_uprn(user_postcode, user_paon)
        check_uprn(user_uprn)
        bindata = {"bins": []}

        URI = "https://bincollections.redditchbc.gov.uk/BinCollections/Details"

        data = {"UPRN": user_uprn}

        # Make the GET request
        response = requests.post(URI, data=data, timeout=30)
        response.raise_for_status()

        # Parse the HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Find all collection containers
        collection_containers = soup.find_all("div", class_="collection-container")

        # Parse each collection container
        for container in collection_containers:
            # Extract bin type (from heading or image alt attribute)
            bin_type = container.find("img")["alt"]

            # Extract the next collection date (from the caption paragraph)
            next_collection = (
                container.find("p", class_="caption")
                .text.replace("Next collection ", "")
                .strip()
            )

            # Extract additional future collection dates (from the list items)
            future_dates = [li.text.strip() for li in container.find_all("li")]

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    next_collection,
                    "%A, %d %B %Y",
                ).strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

            for date in future_dates:  # Add to the schedule
                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(
                        date,
                        "%A, %d %B %Y",
                    ).strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
