import requests
from bs4 import BeautifulSoup

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
        driver = None
        try:
            uri = "https://selfserve.derbyshiredales.gov.uk/renderform.aspx?t=103&k=9644C066D2168A4C21BCDA351DA2642526359DFF"

            bindata = {"bins": []}

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            check_uprn(user_uprn)
            check_postcode(user_postcode)

            # Start a session
            session = requests.Session()

            response = session.get(uri)

            soup = BeautifulSoup(response.content, features="html.parser")

            # Function to extract hidden input values
            def get_hidden_value(soup, name):
                element = soup.find("input", {"name": name})
                return element["value"] if element else None

            # Extract the required values
            data = {
                "__RequestVerificationToken": get_hidden_value(
                    soup, "__RequestVerificationToken"
                ),
                "FormGuid": get_hidden_value(soup, "FormGuid"),
                "ObjectTemplateID": get_hidden_value(soup, "ObjectTemplateID"),
                "Trigger": "submit",
                "CurrentSectionID": get_hidden_value(soup, "CurrentSectionID"),
                "TriggerCtl": "",
                "FF2924": "U" + user_uprn,
                "FF2924lbltxt": "Collection address",
                "FF2924-text": user_postcode,
            }

            # Print extracted data
            # print("Extracted Data:", data)

            # Step 2: Submit the extracted data via a POST request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": uri,
                "Content-Type": "application/x-www-form-urlencoded",
            }

            URI = "https://selfserve.derbyshiredales.gov.uk/renderform/Form"

            # Make the POST request
            post_response = session.post(URI, data=data, headers=headers)

            soup = BeautifulSoup(post_response.content, features="html.parser")

            # print(soup)

            bin_rows = soup.find("div", {"class": "ss_confPanel"})

            bin_rows = bin_rows.find_all("div", {"class": "row"})
            if bin_rows:
                for bin_row in bin_rows:
                    bin_data = bin_row.find_all("div")
                    if bin_data and bin_data[0] and bin_data[1]:
                        if bin_data[0].get_text(strip=True) == "Your Collections":
                            continue
                        collection_date = datetime.strptime(
                            bin_data[0].get_text(strip=True), "%A%d %B, %Y"
                        )
                        dict_data = {
                            "type": bin_data[1].get_text(strip=True),
                            "collectionDate": collection_date.strftime(date_format),
                        }
                        bindata["bins"].append(dict_data)

            bindata["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
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
        return bindata
