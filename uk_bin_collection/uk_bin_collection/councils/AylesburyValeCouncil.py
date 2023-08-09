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
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        # Make SOAP Request
        headers = {
            'Content-Type': 'text/xml; charset=UTF-8',
            'SOAPAction': '"http://tempuri.org/GetCollections"'
        }

        post_data = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope ' \
                    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' \
                    'xmlns:xsd="http://www.w3.org/2001/XMLSchema" ' \
                    'xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><GetCollections ' \
                    'xmlns="http://tempuri.org/"><uprn>' + uprn + '</uprn></GetCollections></soap:Body></soap:Envelope>'

        response = requests.post(
            "http://avdcbins.web-labs.co.uk/RefuseApi.asmx",
            data=post_data,
            headers=headers
        )

        if response.status_code != 200:
            raise ValueError("No collection data found for provided UPRN.")

        # Make a BS4 object
        soup = BeautifulSoup(response.text, "xml")
        soup.prettify()

        data = {"bins": []}

        all_collections = soup.find_all('BinCollection')

        for i in range(len(all_collections)):

            collection_date = datetime.strptime(all_collections[i].Date.get_text(), "%Y-%m-%dT%H:%M:%S")
            # Often the first BinCollection is the previous one
            # The DateTime is set at 7AM so only compare the date element to make sure it captures today's collection at any time of day.
            if collection_date.date() < datetime.today().date():
                continue

            if all_collections[i].Refuse.get_text() == "true":
                bin_type = "Refuse"
                dict_data = {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format)
                }
                data["bins"].append(dict_data)

            if all_collections[i].Recycling.get_text() == "true":
                bin_type = "Recycling"
                dict_data = {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format)
                }
                data["bins"].append(dict_data)

            if all_collections[i].Garden.get_text() == "true":
                bin_type = "Garden"
                dict_data = {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format)
                }
                data["bins"].append(dict_data)

            if all_collections[i].Food.get_text() == "true":
                bin_type = "Food"
                dict_data = {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format)
                }
                data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )
        return data