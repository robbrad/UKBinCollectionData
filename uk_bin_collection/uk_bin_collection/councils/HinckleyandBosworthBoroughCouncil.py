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

        user_uprn = kwargs.get("uprn")
        user_uprn = str(user_uprn).zfill(12)
        check_uprn(user_uprn)
        bindata = {"bins": []}

        URI = f"https://www.hinckley-bosworth.gov.uk/set-location?id={user_uprn}&redirect=refuse&rememberloc="

        # Make the GET request
        response = requests.get(URI)

        # Parse the HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Find all the bin collection date containers
        bin_schedule = []
        collection_divs = soup.find_all(
            "div", class_=["first_date_bins", "last_date_bins"]
        )

        for div in collection_divs:
            # Extract the date
            date = div.find("h3", class_="collectiondate").text.strip().replace(":", "")

            # Extract bin types
            bins = [img["alt"] for img in div.find_all("img", class_="collection")]

            # Append to the schedule
            bin_schedule.append({"date": date, "bins": bins})

        current_year = datetime.now().year
        current_month = datetime.now().month

        # Print the schedule
        for entry in bin_schedule:
            bin_types = entry["bins"]
            date = datetime.strptime(entry["date"], "%d %B")

            if (current_month > 9) and (date.month < 4):
                date = date.replace(year=(current_year + 1))
            else:
                date = date.replace(year=current_year)

            for bin_type in bin_types:

                dict_data = {
                    "type": bin_type,
                    "collectionDate": date.strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
