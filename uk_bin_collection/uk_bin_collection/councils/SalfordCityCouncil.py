from datetime import datetime

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
        user_uprn = kwargs.get("uprn")
        # Check the UPRN is valid
        check_uprn(user_uprn)

        api_url = f"https://www.salford.gov.uk/bins-and-recycling/bin-collection-days/your-bin-collections/?UPRN={user_uprn}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Referer": "https://www.salford.gov.uk/bins-and-recycling/bin-collection-days/",
        }

        # Make a request to the API
        requests.packages.urllib3.disable_warnings()
        response = requests.get(api_url, headers=headers)

        # Use lxml parser — html.parser fails on Salford's malformed HTML
        soup = BeautifulSoup(response.text, features="lxml")

        data = {"bins": []}

        # Get the wastefurther div containing bin type sections
        div_element = soup.find("div", {"class": "wastefurther"})
        if not div_element:
            raise ValueError("Could not find bin collection data — the page structure may have changed")

        # Each bin type is in a col-12 div with a <p><strong>Type:</strong></p> followed by a <ul>
        col_divs = div_element.find_all("div", class_=lambda c: c and "col-12" in c)
        for col in col_divs:
            p_tag = col.find("p")
            if not p_tag:
                continue
            strong_tag = p_tag.find("strong")
            if not strong_tag:
                continue
            bin_type = strong_tag.text.strip()
            # Remove trailing colon
            if bin_type.endswith(":"):
                bin_type = bin_type[:-1]

            ul = col.find("ul")
            if not ul:
                continue

            for li in ul.find_all("li"):
                collection_date = datetime.strptime(li.text.strip(), "%A %d %B %Y")
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": collection_date,
                    }
                )

        # Sort the bins by collection time
        data["bins"] = sorted(data["bins"], key=lambda x: x["collectionDate"])

        # Convert the datetime objects to strings in the desired format
        for bin in data["bins"]:
            bin["collectionDate"] = bin["collectionDate"].strftime(date_format)

        return data
