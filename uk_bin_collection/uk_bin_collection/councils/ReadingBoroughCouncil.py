from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass

class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:

        json_result = json.loads(page.text)

        data = {"bins": []}

        for collection in json_result['collections']:
            bin_type = collection['service']
            bin_collection = collection['date'] # Date format is 14/12/2023 00:00:00

            dict_data = {
                "type": bin_type.replace(" Collection Service"," Bin"),
                "collectionDate": datetime.strptime(bin_collection, "%d/%m/%Y %H:%M:%S").strftime(date_format)
            }

            data["bins"].append(dict_data)

        return data
