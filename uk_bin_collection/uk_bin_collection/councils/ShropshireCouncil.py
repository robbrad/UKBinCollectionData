from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        # Form a JSON wrapper
        data = {"bins": []}

        # Find section with bins in
        wrapper = soup.find("div", {"class": "container results-table-wrapper"})
        if not wrapper:
            raise ValueError("Could not find results table wrapper")
        tbody = wrapper.find("tbody")
        if not tbody:
            raise ValueError("Could not find table body")
        sections = tbody.find_all("tr")

        # For each bin section, get the text and the list elements
        for item in sections:
            service_name_td = item.find("td", {"class": "service-name"})
            if not service_name_td:
                continue

            # Use the full link text as the bin type
            a_tag = service_name_td.find("a")
            if a_tag:
                bin_type = a_tag.text.strip()
            else:
                continue

            next_service_td = item.find("td", {"class": "next-service"})
            if not next_service_td:
                continue

            # The date is after the first span (table-label) as a text node
            span = next_service_td.find("span", {"class": "table-label"})
            if span and span.next_sibling:
                date_text = str(span.next_sibling).strip()
            else:
                # Fallback: get direct text content
                date_text = next_service_td.get_text(strip=True)
                # Remove the "Next collection" label text
                date_text = date_text.replace("Next collection", "").replace("Next Collections", "").strip()

            if not date_text:
                continue

            # Handle multiple dates (comma-separated)
            date_parts = [d.strip() for d in date_text.split(",") if d.strip()]
            for date_str in date_parts:
                try:
                    next_collection = datetime.strptime(date_str, "%d/%m/%Y")
                except ValueError:
                    try:
                        next_collection = datetime.strptime(date_str, "%d %b %Y")
                    except ValueError:
                        continue

                dict_data = {
                    "type": bin_type,
                    "collectionDate": next_collection.strftime(date_format),
                }
                data["bins"].append(dict_data)

        return data
