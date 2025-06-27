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
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
        }
        response = requests.post(
            "https://www.rotherham.gov.uk/bin-collections?address={}&submit=Submit".format(
                user_uprn
            ), 
            headers=headers
        )
        # Make a BS4 object
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        table = soup.select("table")[0]

        if table:
            rows = table.select("tr")

            for index, row in enumerate(rows):
                bin_info_cell = row.select("td")
                if bin_info_cell:
                    bin_type = bin_info_cell[0].get_text(separator=" ", strip=True)
                    bin_collection = bin_info_cell[1]

                    if bin_collection:
                        dict_data = {
                            "type": bin_type.title(),
                            "collectionDate": datetime.strptime(
                                bin_collection.get_text(strip=True), "%A, %d %B %Y"
                            ).strftime(date_format),
                        }

                    data["bins"].append(dict_data)
        else:
            print("Something went wrong. Please open a GitHub issue.")

        return data
