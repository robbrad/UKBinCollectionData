from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def get_token(page) -> str:
    """
    Get a __token to include in the form data
        :param page: Page html
        :return: Form __token
    """
    soup = BeautifulSoup(page.text, features="html.parser")
    soup.prettify()
    token = soup.find("input", {"name": "__token"}).get("value")
    return token


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        postcode = kwargs.get("postcode")
        check_uprn(uprn)
        check_postcode(postcode)

        values = {
            "__token": get_token(page),
            "page": "492",
            "locale": "en_GB",
            "q9f451fe0ca70775687eeedd1e54b359e55f7c10c_0_0": postcode,
            "q9f451fe0ca70775687eeedd1e54b359e55f7c10c_1_0": uprn,
            "next": "Next",
        }
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}
        requests.packages.urllib3.disable_warnings()
        response = requests.request(
            "POST",
            "https://www.welhat.gov.uk/xfp/form/214",
            headers=headers,
            data=values,
        )

        soup = BeautifulSoup(response.text, features="html.parser")

        rows = soup.find("table").find_all("tr")

        # Form a JSON wrapper
        data = {"bins": []}

        # Loops the Rows
        for row in rows:
            cells = row.find_all("td")
            if cells:
                binType = cells[0].get_text(strip=True)
                collectionDate = datetime.strptime(
                    cells[1].get_text(strip=True), "%A %d %B  %Y"
                ).strftime(date_format)

                # Make each Bin element in the JSON
                dict_data = {
                    "type": binType,
                    "collectionDate": collectionDate,
                }

                # Add data to the main JSON Wrapper
                data["bins"].append(dict_data)

        return data
