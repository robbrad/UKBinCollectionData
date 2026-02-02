import requests
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Parser for London Borough of Camden Council
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)

        # Build the property URL
        property_url = f"https://environmentservices.camden.gov.uk/property/{user_uprn}"

        # Make the request
        response = requests.get(property_url)
        response.raise_for_status()

        # Parse the HTML
        soup = BeautifulSoup(response.content, "html.parser")

        data = {"bins": []}

        # Find all service wrappers
        service_wrappers = soup.find_all("div", class_="service-wrapper")

        for service in service_wrappers:
            # Get the service name (bin type)
            service_name_elem = service.find("h3", class_="service-name")
            if not service_name_elem:
                continue

            bin_type = service_name_elem.get_text(strip=True)
            # Remove "Add to my calendar" text if present
            bin_type = bin_type.replace("Add to my calendar", "").strip()

            # Find the next collection date
            next_collection_elem = service.find("td", class_="next-service")
            if not next_collection_elem:
                continue

            next_collection_date = next_collection_elem.get_text(strip=True)

            # Parse the date (format: dd/mm/yyyy)
            try:
                collection_date = datetime.strptime(
                    next_collection_date, "%d/%m/%Y"
                )
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )
            except ValueError:
                # Skip if date parsing fails
                continue

        return data
