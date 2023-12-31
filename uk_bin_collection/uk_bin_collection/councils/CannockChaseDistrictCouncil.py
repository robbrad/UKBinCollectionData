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

        # Make SOAP Request
        response = requests.post(
            "https://ccdc.opendata.onl/DynamicCall.dll",
            data="Method=CollectionDates&Postcode="
            + user_postcode
            + "&UPRN="
            + user_uprn,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://ccdc.opendata.onl/CCDC_WasteCollection",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            },
        )

        # Make a BS4 object
        soup = BeautifulSoup(response.text, "xml")
        soup.prettify()

        if (
            soup.find("ErrorDescription")
            and soup.find("ErrorDescription").get_text(strip=True)
            == "No results returned"
        ):
            raise ValueError("No collection data found for provided Postcode & UPRN.")

        data = {"bins": []}

        collections = soup.find_all("Collection")

        for i in range(len(collections)):
            dict_data = {
                "type": collections[i]
                .Service.get_text()
                .replace("Collection Service", "")
                .strip(),
                "collectionDate": datetime.strptime(
                    collections[i].Date.get_text(), "%d/%m/%Y %H:%M:%S"
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )
        return data
