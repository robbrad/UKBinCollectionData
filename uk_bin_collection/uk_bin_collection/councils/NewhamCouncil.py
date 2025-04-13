import urllib3
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        # get the page data
        http = urllib3.PoolManager()
        response = http.request("GET", kwargs["url"])
        page_data = response.data

        # Make a BS4 object
        soup = BeautifulSoup(page_data, features="html.parser")
        soup.prettify()

        # Form a JSON wrapper
        data = {"bins": []}

        # Find section with bins in
        sections = soup.find_all("div", {"class": "card h-100"})

        # there may also be a recycling one too
        sections_recycling = soup.find_all(
            "div", {"class": "card h-100 card-recycling"}
        )
        if len(sections_recycling) > 0:
            sections.append(sections_recycling[0])

        # For each bin section, get the text and the list elements
        for item in sections:
            header = item.find("div", {"class": "card-header"})
            bin_type_element = header.find_next("b")
            if bin_type_element is not None:
                bin_type = bin_type_element.text
                array_expected_types = ["Domestic", "Recycling"]
                if bin_type in array_expected_types:
                    date = (
                        item.find_next("p", {"class": "card-text"})
                        .find_next("mark")
                        .next_sibling.strip()
                    )
                    next_collection = datetime.strptime(date, "%d/%m/%Y")

                    dict_data = {
                        "type": bin_type,
                        "collectionDate": next_collection.strftime(date_format),
                    }
                    data["bins"].append(dict_data)

        return data
