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
        api_url = "https://webforms.rochdale.gov.uk/BinCalendar"
        user_postcode = kwargs.get("postcode")
        user_uprn = kwargs.get("uprn")

        # Check the postcode and UPRN are valid
        check_postcode(user_postcode)
        check_uprn(user_uprn)

        # Create the form data
        form_data = {
            "PostCode": user_postcode,
            "SelectedUprn": user_uprn,
            "Step": 2,
        }

        # Make a request to the API
        response = requests.post(api_url, data=form_data)

        # Make a BS4 object
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        # Get the table element and rows
        table_element = soup.find("table", {"id": "tblCollectionDetails"})
        table_rows = table_element.find_all_next("tr")

        row_index = 0
        for row in table_rows:
            if row_index < 1:
                row_index += 1
                continue
            else:
                # Get the date from the th element
                date = row.find("th").get_text().strip()

                # Get the bin types from the td elements and filter out the empty ones
                bin_types = filter(lambda td: td.find("img"), row.find_all("td"))

                # Convert the bin types to a list
                bin_types_list = list(bin_types)

                # Append the bin type and date to the data dict
                for td in bin_types_list:
                    img = td.find("img")
                    bin_type_text = img["alt"]
                    data["bins"].append({"type": bin_type_text, "collectionDate": date})

                row_index += 1

        return data
