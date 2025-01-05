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

        URI = "https://waste.cumberland.gov.uk/renderform?t=25&k=E43CEB1FB59F859833EF2D52B16F3F4EBE1CAB6A"

        s = requests.Session()

        # Make the GET request
        response = s.get(URI)

        # Make a BS4 object
        soup = BeautifulSoup(response.content, features="html.parser")

        # print(soup)

        token = (soup.find("input", {"name": "__RequestVerificationToken"})).get(
            "value"
        )

        formguid = (soup.find("input", {"name": "FormGuid"})).get("value")

        # print(token)
        # print(formguid)

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://waste.cumberland.gov.uk",
            "Referer": "https://waste.cumberland.gov.uk/renderform?t=25&k=E43CEB1FB59F859833EF2D52B16F3F4EBE1CAB6A",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 OPR/98.0.0.0",
            "X-Requested-With": "XMLHttpRequest",
        }

        payload = {
            "__RequestVerificationToken": token,
            "FormGuid": formguid,
            "ObjectTemplateID": "25",
            "Trigger": "submit",
            "CurrentSectionID": "33",
            "TriggerCtl": "",
            "FF265": f"U{user_uprn}",
            "FF265lbltxt": "Please select your address",
        }

        # print(payload)

        response = s.post(
            "https://waste.cumberland.gov.uk/renderform/Form",
            headers=headers,
            data=payload,
        )

        soup = BeautifulSoup(response.content, features="html.parser")
        for row in soup.find_all("div", class_="resirow"):
            # Extract the type of collection (e.g., Recycling, Refuse)
            collection_type_div = row.find("div", class_="col")
            collection_type = (
                collection_type_div.get("class")[1]
                if collection_type_div
                else "Unknown"
            )

            # Extract the collection date
            date_div = row.find("div", style="width:360px;")
            collection_date = date_div.text.strip() if date_div else "Unknown"

            dict_data = {
                "type": collection_type,
                "collectionDate": datetime.strptime(
                    collection_date, "%A %d %B %Y"
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
