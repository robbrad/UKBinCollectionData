from bs4 import BeautifulSoup
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
        api_url = "https://forms.n-somerset.gov.uk/Waste/CollectionSchedule"
        uprn = kwargs.get("uprn")
        postcode = kwargs.get("postcode")
        check_uprn(uprn)
        check_postcode(postcode)

        # Get schedule from API
        values = {
            "PreviousHouse": "",
            "PreviousPostcode": postcode,
            "Postcode": postcode,
            "SelectedUprn": uprn,
        }
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}
        requests.packages.urllib3.disable_warnings()
        response = requests.request("POST", api_url, headers=headers, data=values)

        soup = BeautifulSoup(response.text, features="html.parser")

        rows = soup.find("table", {"class": re.compile("table")}).find_all("tr")

        # Form a JSON wrapper
        data = {"bins": []}

        # Loops the Rows
        for row in rows:
            cells = row.find_all("td")
            if cells:
                binType = cells[0].get_text(strip=True)
                collectionDate = cells[1].get_text(strip=True) + " " + datetime.now().strftime("%Y")
                nextCollectionDate = cells[2].get_text(strip=True) + " " + datetime.now().strftime("%Y")

                # Make each Bin element in the JSON
                dict_data = {
                    "type": binType,
                    "collectionDate": get_next_occurrence_from_day_month(
                        datetime.strptime(collectionDate, "%A %d %B %Y")
                    ).strftime(date_format)
                }

                # Add data to the main JSON Wrapper
                data["bins"].append(dict_data)

                # Make each next Bin element in the JSON
                dict_data = {
                    "type": binType,
                    "collectionDate": get_next_occurrence_from_day_month(
                        datetime.strptime(nextCollectionDate, "%A %d %B %Y")
                    ).strftime(date_format),
                }

                # Add data to the main JSON Wrapper
                data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
