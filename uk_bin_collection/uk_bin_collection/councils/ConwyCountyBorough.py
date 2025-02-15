from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        uri = f"https://www.conwy.gov.uk/Contensis-Forms/erf/collection-result-soap-xmas2025.asp?ilangid=1&uprn={user_uprn}"

        response = requests.get(uri)
        soup = BeautifulSoup(response.content, features="html.parser")
        data = {"bins": []}

        for bin_section in soup.select('div[class*="containererf"]'):
            date_text = bin_section.find(id="content").text.strip()
            collection_date = datetime.strptime(date_text, "%A, %d/%m/%Y")

            bin_types = bin_section.find(id="main1").findAll("li")
            for bin_type in bin_types:
                bin_type_name = bin_type.text.split("(")[0].strip()

                data["bins"].append(
                    {
                        "type": bin_type_name,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )

        return data
