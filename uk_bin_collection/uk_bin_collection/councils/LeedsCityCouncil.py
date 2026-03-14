from datetime import datetime

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        data = {"bins": []}
        try:
            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)

            URI = "https://api.leeds.gov.uk/public/waste/v1/BinsDays"

            startDate = datetime.now()
            endDate = (startDate + timedelta(weeks=8)).strftime("%Y-%m-%d")
            startDate = startDate.strftime("%Y-%m-%d")

            params = {
                "uprn": user_uprn,
                "startDate": startDate,
                "endDate": endDate,
            }

            headers = {
                "ocp-apim-subscription-key": "ad8dd80444fe45fcad376f82cf9a5ab4",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            }

            # print(params)

            # Send GET request
            response = requests.get(URI, params=params, headers=headers)

            print(response.content)

            collections = json.loads(response.content)

            for collection in collections:

                collectionDate = datetime.strptime(
                    collection["date"], "%Y-%m-%dT%H:%M:%S"
                )

                data["bins"].append(
                    {
                        "type": collection["type"],
                        "collectionDate": collectionDate.strftime(date_format),
                    }
                )

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return data
