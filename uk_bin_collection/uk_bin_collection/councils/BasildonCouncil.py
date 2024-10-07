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
        url_base = "https://basildonportal.azurewebsites.net/api/getPropertyRefuseInformation"

        uprn = kwargs.get("uprn")
        # Check the UPRN is valid
        check_uprn(uprn)

        payload = {
            # Add your payload details here (replace this with the actual payload structure if required)
            "uprn": uprn
        }

        # Headers for the request
        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(url_base, data=json.dumps(payload), headers=headers)

        # Ensure the request was successful
        if response.status_code == 200:
            data = response.json()

            # Initialize an empty list to store the bin collection details

            bins = []

            # Function to add collection details to bins list
            def add_collection(service_name, collection_data):
                bins.append({
                    "type": service_name,
                    "collectionDate": collection_data.get("current_collection_date")
                })

            # Extract refuse information
            available_services = data["refuse"]["available_services"]

            for service_name, service_data in available_services.items():
                # Append the service name and current collection date to the "bins" list
                match service_data["container"]:
                    case "Green Wheelie Bin":
                        subscription_status = service_data["subscription"]["active"] if service_data["subscription"] else False
                        type_descr = f"Green Wheelie Bin ({"Active" if subscription_status else "Expired"})"
                    case "N/A":
                        type_descr = service_data["name"]
                    case _:
                        type_descr = service_data["container"]


                date_str = service_data.get("current_collection_date")
                # Parse the date string into a datetime object
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")

                # Convert the datetime object to the desired format
                formatted_date = date_obj.strftime(date_format)

                bins.append({
                    "type": type_descr,  # Use service name from the data
                    "collectionDate": formatted_date
                })

        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")

        data = {
            "bins": bins
        }

        return data
