import json
from datetime import datetime

import requests
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


def get_address_uprn(postcode: str, paon: str, api_url: str) -> str:
    """
    Gets the UPRN and address in desired format
        :rtype: str
        :param postcode: Postcode to use
        :param paon: House number to use
        :param api_url: API to POST
        :return: UPRN and postcode in str format
    """
    addr = ""
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "1642260173663",
            "method": "ictGetAddressList",
            "params": {"postcode": f"{postcode.replace(' ', '')}", "localonly": "true"},
        }
    )
    headers = {"Content-Type": "application/json"}
    response = requests.post(api_url, data=payload, headers=headers)

    json_response = json.loads(response.content)
    results = json_response["result"]
    result_line = ""

    for item in results:
        while len(result_line) < 1:
            result_line = [
                element
                for element in item.get("Address").split()
                if item.get("Address").split()[0] == paon.strip()
            ]
            addr = item.get("UPRN") + "|" + item.get("Address")
            break

    return addr


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        requests.packages.urllib3.disable_warnings()
        api_url = "https://www.southtyneside.gov.uk/apiserver/ajaxlibrary/"
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        data = {"bins": []}

        check_postcode(user_postcode)
        check_paon(user_paon)

        try:
            if user_paon is None:
                raise ValueError("Invalid house number")
        except Exception as ex:
            print(f"Exception encountered: {ex}")
            print(
                "Please check the provided house number. If this error continues, please first trying setting the "
                "house number manually on line 25 before raising an issue."
            )
            exit(1)

        # Get the "UPRN" (actually the UPRN + address)
        uprn = get_address_uprn(user_postcode, user_paon, api_url)

        # Set up payload and headers, then post to API to get schedule
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "1642260412610",
                "method": "wtGetBinCollectionDates",
                "params": {"addresscode": uprn},
            }
        )
        headers = {"Content-Type": "application/json"}
        response = requests.request("POST", api_url, headers=headers, data=payload)

        # Break down the resulting JSON and load into dictionary
        json_result = json.loads(response.text)["result"]
        months = json_result["SortedCollections"]
        for month in months:
            collections_in_month = month["Collections"]
            for item in collections_in_month:
                dict_data = {
                    "type": item["Type"],
                    "collectionDate": datetime.strptime(
                        item["DateString"], "%d %B %Y"
                    ).strftime("%d/%m/%Y"),
                }
                data["bins"].append(dict_data)

        return data
