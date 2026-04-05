import requests
from bs4 import BeautifulSoup
from datetime import datetime

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str = None, **kwargs) -> dict:
        try:
            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)
            url = f"https://bincollection.newham.gov.uk/Details/Index/{user_uprn}"
            if not user_uprn:
                url = kwargs.get("url")
                if not url:
                    raise ValueError("No UPRN or URL provided")
        except Exception as e:
            raise ValueError(f"Error getting identifier: {str(e)}")

        # Fetch page
        page = requests.get(url, verify=False)
        soup = BeautifulSoup(page.text, "html.parser")

        # Prepare JSON wrapper
        data = {"bins": []}

        # Find all relevant bin sections
        sections = soup.find_all("div", {"class": "card h-100"})
        # Include recycling section
        sections_recycling = soup.find_all("div", {"class": "card h-100 card-recycling"})
        if sections_recycling:
            sections.append(sections_recycling[0])
        # Include food waste section
        sections_food_waste = soup.find_all("div", {"class": "card h-100 card-food"})
        if sections_food_waste:
            sections.append(sections_food_waste[0])

        # Process each section
        for item in sections:
            header = item.find("div", {"class": "card-header"})
            bin_type_element = header.find_next("b") if header else None

            if not bin_type_element:
                continue  # skip if no bin type found

            bin_type = bin_type_element.text.strip()
            expected_types = ["Domestic", "Recycling", "Food Waste"]

            if bin_type not in expected_types:
                continue  # skip unexpected types

            # Find date safely
            p_element = item.find_next("p", {"class": "card-text"})
            mark_element = p_element.find_next("mark") if p_element else None

            if not mark_element:
                continue  # skip if no date mark found

            date_text = mark_element.next_sibling
            if not date_text:
                # fallback: get next text node
                date_text = mark_element.find_next(text=True)
            if not date_text:
                continue  # skip if still no text

            date_text = date_text.strip()

            # Parse date
            try:
                next_collection = datetime.strptime(date_text, "%m/%d/%Y")
            except ValueError:
                continue  # skip invalid date formats

            # Add to data
            data["bins"].append({
                "type": bin_type,
                "collectionDate": next_collection.strftime(date_format),
            })

        return data
