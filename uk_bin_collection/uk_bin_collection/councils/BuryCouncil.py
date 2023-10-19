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
        # Make a BS4 object
        collections = []
        data = {"bins": []}

        # Get and check postcode and PAON
        postcode = kwargs.get('postcode')
        paon = kwargs.get('paon')
        check_postcode(postcode)
        check_paon(paon)

        # Make API call to get property info using postcode
        addr_response = requests.get(
            f'https://www.bury.gov.uk/app-services/getProperties?postcode={postcode.replace(" ", "")}')
        if addr_response.status_code != 200:
            raise ConnectionAbortedError("Issue encountered getting addresses.")
        address_json = json.loads(addr_response.text)['response']

        # This makes addr the next item that has the house number. Since these are ordered by house number, a single
        # number like 3 wouldn't return 33
        addr = next(item for item in address_json if paon in item["addressLine1"])

        # Make API call to get bin data using property ID
        response = requests.get(f'https://www.bury.gov.uk/app-services/getPropertyById?id={addr.get("id")}')
        if response.status_code != 200:
            raise ConnectionAbortedError("Issue encountered getting bin data.")
        bin_list = json.loads(response.text)['response']['bins']

        # The JSON actually returns the next collections and a large calendar. But I opted just for the next dates.
        for bin_colour, collection_data in bin_list.items():
            bin_type = bin_colour
            bin_date = datetime.strptime(remove_ordinal_indicator_from_date_string(collection_data.get('nextCollection')), "%A %d %B %Y")
            collections.append((bin_type, bin_date))

        # Dates are ordered correctly - soonest first
        ordered_data = sorted(collections, key=lambda x: x[1])
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
