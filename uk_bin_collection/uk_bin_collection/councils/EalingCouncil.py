import json
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        api_url = "https://www.ealing.gov.uk/site/custom_scripts/WasteCollectionWS/home/FindCollection"
        user_uprn = kwargs.get("uprn")

        # Check the UPRN is valid
        check_uprn(user_uprn)

        # Create the form data
        form_data = {
            "UPRN": user_uprn,
        }

        # Make a request to the API
        requests.packages.urllib3.disable_warnings()
        response = requests.post(api_url, data=form_data)

        json_data = json.loads(response.text)

        data = {"bins": []}

        for param in json_data["param2"]:
            data["bins"].append(
                {
                    "type": param["Service"],
                    "collectionDate": datetime.strptime(
                        param["collectionDateString"], "%d/%m/%Y"
                    ).strftime(date_format),
                }
            )

        return data
