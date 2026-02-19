import requests
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
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        # Direct URL to the bin collection schedule using UPRN
        url = f"https://www.cumberland.gov.uk/bins-recycling-and-street-cleaning/waste-collections/bin-collection-schedule/view/{user_uprn}"

        # Fetch the page
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Find the content region
        content_region = soup.find("div", class_="lgd-region--content")
        if not content_region:
            return bindata

        # Parse the text content to extract collection dates
        text_content = content_region.get_text()
        lines = [line.strip() for line in text_content.split("\n") if line.strip()]

        current_month = None
        current_year = datetime.now().year
        previous_month_num = 0
        i = 0

        # Determine the base year from the page heading, e.g.
        # "Collection calendar: February to August 2026"
        # This is more reliable than checking whether "2026" appears anywhere
        # in the page, which broke the year assignment for all non-Jan/Feb months.
        for line in lines:
            if "Collection calendar" in line:
                for word in reversed(line.split()):
                    if word.isdigit() and len(word) == 4:
                        current_year = int(word)
                        break
                break

        while i < len(lines):
            line = lines[i]

            # Check if this is a month name
            if line in [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December",
            ]:
                month_num = datetime.strptime(line, "%B").month

                # If months go backwards (e.g. December -> January),
                # we have crossed into the next year
                if month_num < previous_month_num:
                    current_year += 1

                previous_month_num = month_num
                current_month = line
                i += 1
                continue

            # Check if this is a day number (1-31)
            if line.isdigit() and 1 <= int(line) <= 31 and current_month:
                day = line

                # Next line should be the bin type
                if i + 1 < len(lines):
                    bin_type = lines[i + 1]

                    # Skip the subtype line (e.g. Refuse, Recycling, Paper, Green)
                    # A subtype is any line that is neither a digit nor a month name
                    if (
                        i + 2 < len(lines)
                        and not lines[i + 2].isdigit()
                        and lines[i + 2] not in [
                            "January", "February", "March", "April", "May", "June",
                            "July", "August", "September", "October", "November", "December",
                        ]
                    ):
                        i += 1

                    # Parse the date
                    try:
                        date_str = f"{day} {current_month} {current_year}"
                        collection_date = datetime.strptime(date_str, "%d %B %Y")

                        dict_data = {
                            "type": bin_type,
                            "collectionDate": collection_date.strftime(date_format),
                        }
                        bindata["bins"].append(dict_data)
                    except ValueError:
                        pass

                    i += 2
                    continue

            i += 1

        # Sort by collection date
        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )
        return bindata
