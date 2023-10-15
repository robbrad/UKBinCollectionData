from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        api_url = "https://swict.malvernhills.gov.uk/mhdcroundlookup/HandleSearchScreen"

        user_uprn = kwargs.get("uprn")
        # Check the UPRN is valid
        check_uprn(user_uprn)

        # Create the form data
        form_data = {"nmalAddrtxt": "", "alAddrsel": user_uprn}
        # expects postcode to be looked up and then uprn used.
        # we can just provide uprn

        # Make a request to the API
        requests.packages.urllib3.disable_warnings()
        response = requests.post(api_url, data=form_data, verify=False)

        # Make a BS4 object
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        # Find results table
        table_element = soup.find("table")
        table_body = table_element.find("tbody")
        rows = table_body.find_all("tr")

        data = {"bins": []}

        for row in rows:
            columns = row.find_all("td")
            columns = [ele.text.strip() for ele in columns]

            thisCollection = [ele for ele in columns if ele]  # Get rid of empty values

            # if not signed up for garden waste, this appears as Not applicable
            if "Not applicable" not in thisCollection[1]:
                bin_type = thisCollection[0].replace("collection", "").strip()
                date = datetime.strptime(thisCollection[1], "%A %d/%m/%Y")
                dict_data = {
                    "type": bin_type,
                    "collectionDate": date.strftime(date_format),
                }
                data["bins"].append(dict_data)

        return data
