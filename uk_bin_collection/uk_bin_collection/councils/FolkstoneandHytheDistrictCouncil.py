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
        check_uprn(user_uprn)
        bindata = {"bins": []}

        URI = f"https://service.folkestone-hythe.gov.uk/webapp/myarea/index.php?uprn={user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        soup = BeautifulSoup(response.content, "html.parser")

        soup = soup.find("div", {"id": "bincollections"})

        # Find the Recycling and Non-Recyclables sections
        bin_schedule = {}

        # Extract the recycling schedule
        recycling_section = soup.find("span", text=lambda x: x and "Recycling" in x)
        if recycling_section:
            bin_types = recycling_section.text.replace("Recycling: ", "").split(" / ")
            recycling_dates = recycling_section.find_next("ul").find_all("li")
            bin_schedule["Recycling"] = [date.text.strip() for date in recycling_dates]
            for date in recycling_dates:
                for bin_type in bin_types:
                    dict_data = {
                        "type": bin_type.strip(),
                        "collectionDate": datetime.strptime(
                            remove_ordinal_indicator_from_date_string(
                                date.text.strip()
                            ),
                            "%A %d %B %Y",
                        ).strftime("%d/%m/%Y"),
                    }
                    bindata["bins"].append(dict_data)

        # Extract the non-recyclables schedule
        non_recyclables_section = soup.find(
            "span", text=lambda x: x and "Non-Recyclables" in x
        )
        if non_recyclables_section:
            bin_types = non_recyclables_section.text.replace(
                "Non-Recyclables: ", ""
            ).split(" / ")
            non_recyclables_dates = non_recyclables_section.find_next("ul").find_all(
                "li"
            )
            for date in non_recyclables_dates:
                for bin_type in bin_types:
                    dict_data = {
                        "type": bin_type.strip(),
                        "collectionDate": datetime.strptime(
                            remove_ordinal_indicator_from_date_string(
                                date.text.strip()
                            ),
                            "%A %d %B %Y",
                        ).strftime("%d/%m/%Y"),
                    }
                    bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
