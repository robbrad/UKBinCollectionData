import requests
import json
from datetime import datetime
from uk_bin_collection.uk_bin_collection.common import (
    check_uprn,
    date_format as DATE_FORMAT,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete class that implements the abstract bin data fetching and parsing logic.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        url_base = (
            "https://basildonportal.azurewebsites.net/api/getPropertyRefuseInformation"
        )

        uprn = kwargs.get("uprn")
        # Check the UPRN is valid
        check_uprn(uprn)

        payload = {"uprn": uprn}

        headers = {"Content-Type": "application/json"}

        response = requests.post(url_base, data=json.dumps(payload), headers=headers)

        if response.status_code == 200:
            data = response.json()

            # Initialize an empty list to store the bin collection details
            bins = []

            # Function to add collection details to bins list
            def add_collection(service_name, collection_data):
                bins.append(
                    {
                        "type": service_name,
                        "collectionDate": collection_data.get(
                            "current_collection_date"
                        ),
                    }
                )

            available_services = data.get("refuse", {}).get("available_services", {})

            date_format = "%d-%m-%Y"  # Define the desired date format

            for service_name, service_data in available_services.items():
                # Handle the different cases of service data
                match service_data["container"]:
                    case "Green Wheelie Bin":
                        subscription_status = (
                            service_data["subscription"]["active"]
                            if service_data.get("subscription")
                            else False
                        )
                        type_descr = f"Green Wheelie Bin ({'Active' if subscription_status else 'Expired'})"
                    case "N/A":
                        type_descr = service_data.get("name", "Unknown Service")
                    case _:
                        type_descr = service_data.get("container", "Unknown Container")

                date_str = service_data.get("current_collection_date")
                if date_str:  # Ensure the date string exists
                    try:
                        # Parse and format the date string
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_date = date_obj.strftime(DATE_FORMAT)
                    except ValueError:
                        formatted_date = "Invalid Date"
                else:
                    formatted_date = "No Collection Date"

                bins.append(
                    {
                        "type": type_descr,  # Use service name from the data
                        "collectionDate": formatted_date,
                    }
                )

        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            return {}

        return {"bins": bins}
