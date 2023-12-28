from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        response = requests.post(
            f"https://wastecollections.haringey.gov.uk/property/{uprn}"
        )
        if response.status_code != 200:
            raise ConnectionAbortedError("Issue encountered getting addresses.")

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        sections = soup.find_all("div", {"class": "property-service-wrapper"})

        date_regex = re.compile(r"\d{2}/\d{2}/\d{4}")
        for section in sections:
            service = section.find("h3", {"class": "service-name"}).text
            next_collection = (
                section.find("tbody")
                .find("td", {"class": "next-service"})
                .find(text=date_regex)
            )
            # Remove Collect and Collect Paid from the start of some bin entry names
            # to make the naming more consistant.
            dict_data = {
                "type": service.replace("Collect ", "").replace("Paid ", "").strip(),
                "collectionDate": next_collection.strip(),
            }
            data["bins"].append(dict_data)

        return data
