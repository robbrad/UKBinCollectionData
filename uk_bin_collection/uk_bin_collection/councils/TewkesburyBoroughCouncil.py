import time

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        epoch_time = int(time.time())

        URI = f"https://api-2.tewkesbury.gov.uk/incab/rounds/{user_uprn}/next-collection?_={epoch_time}"

        # Make the GET request
        response = requests.get(URI)

        data = {"bins": []}

        for collections in json.loads(response.content)["body"]:
            collection_date = datetime.strptime(
                collections["NextCollection"], "%Y-%m-%d"
            )
            dict_data = {
                "type": collections["collectionType"],
                "collectionDate": collection_date.strftime(date_format),
            }
            data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return data
