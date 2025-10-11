from bs4 import BeautifulSoup
from dateutil.parser import parse

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        api_url = f"https://www.islington.gov.uk/your-area?Postcode=unused&Uprn={uprn}"
        response = requests.get(api_url)

        soup = BeautifulSoup(response.text, features="html.parser")

        data = {"bins": []}

        # Find the waste and recycling section with proper null checking
        waste_section = soup.find(string="Waste and recycling collections")
        waste_table = None
        
        if waste_section:
            toggle_content = waste_section.find_next("div", class_="m-toggle-content")
            if toggle_content:
                waste_table = toggle_content.find("table")

        if waste_table:
            rows = waste_table.find_all("tr")
            for row in rows:
                waste_type = row.find("th").text.strip()
                next_collection = parse(row.find("td").text.strip()).date()

                data["bins"].append(
                    {
                        "type": waste_type,
                        "collectionDate": next_collection.strftime(date_format),
                    }
                )

        return data
