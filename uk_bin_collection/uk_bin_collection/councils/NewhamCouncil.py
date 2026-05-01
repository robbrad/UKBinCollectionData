import urllib3
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:

        try:
            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)
            url = f"https://bincollection.newham.gov.uk/Details/Index/{user_uprn}"
            if not user_uprn:
                # This is a fallback for if the user stored a URL in old system. Ensures backwards compatibility.
                url = kwargs.get("url")
        except Exception as e:
            raise ValueError(f"Error getting identifier: {str(e)}")

        # Make a BS4 object
        page = requests.get(url, verify=False)
        soup = BeautifulSoup(page.text, "html.parser")
        soup.prettify

        # Form a JSON wrapper
        data = {"bins": []}

        # Find all card sections (domestic, recycling, food, garden)
        all_cards = soup.find_all("div", class_=lambda c: c and "card" in c and "h-100" in c)

        # For each bin section, get the text and the list elements
        for item in all_cards:
            header = item.find("div", {"class": "card-header"})
            if not header:
                continue
            bin_type_element = header.find_next("b")
            if bin_type_element is None:
                continue
            bin_type = bin_type_element.text
            array_expected_types = ["Domestic", "Recycling", "Food Waste"]
            if bin_type not in array_expected_types:
                continue

            # Find the card-text paragraph with the date
            card_text = item.find("p", {"class": "card-text"})
            if not card_text:
                continue

            mark_tag = card_text.find("mark")
            if not mark_tag:
                continue

            # The date is in the next_sibling after the mark tag
            # Format changed: was "mm/dd/yyyy" after mark, now "\xa0mm/dd/yyyy" or similar
            next_sib = mark_tag.next_sibling
            if next_sib is None:
                # Try getting text after mark from the <br> tag's next sibling
                br_tag = mark_tag.find_next("br")
                if br_tag and br_tag.next_sibling:
                    next_sib = br_tag.next_sibling
                else:
                    continue

            date_str = str(next_sib).strip().replace("\xa0", "")
            if not date_str:
                continue

            try:
                next_collection = datetime.strptime(date_str, "%m/%d/%Y")
            except ValueError:
                try:
                    next_collection = datetime.strptime(date_str, "%d/%m/%Y")
                except ValueError:
                    continue

            dict_data = {
                "type": bin_type,
                "collectionDate": next_collection.strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
