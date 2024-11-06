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
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)
        bindata = {"bins": []}

        session_uri = "https://www.oxford.gov.uk/mybinday"
        URI = "https://www.oxford.gov.uk/xfp/form/142"

        session = requests.Session()
        token_response = session.get(session_uri)
        soup = BeautifulSoup(token_response.text, "html.parser")
        token = soup.find("input", {"name": "__token"}).attrs["value"]

        form_data = {
            "__token": token,
            "page": "12",
            "locale": "en_GB",
            "q6ad4e3bf432c83230a0347a6eea6c805c672efeb_0_0": user_postcode,
            "q6ad4e3bf432c83230a0347a6eea6c805c672efeb_1_0": user_uprn,
            "next": "Next",
        }

        collection_response = session.post(URI, data=form_data)

        collection_soup = BeautifulSoup(collection_response.text, "html.parser")
        for paragraph in collection_soup.find("div", class_="editor").find_all("p"):
            matches = re.match(r"^(\w+) Next Collection: (.*)", paragraph.text)
            if matches:
                collection_type, date_string = matches.groups()
                try:
                    date = datetime.strptime(date_string, "%A %d %B %Y").date()
                except ValueError:
                    date = datetime.strptime(date_string, "%A %d %b %Y").date()

                dict_data = {
                    "type": collection_type,
                    "collectionDate": date.strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
