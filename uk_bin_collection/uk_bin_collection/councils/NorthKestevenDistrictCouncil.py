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
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        # Find the bin-dates div
        bin_dates_div = soup.find("div", {"class": "bin-dates"})
        if not bin_dates_div:
            return data

        # Find all list items with bin collection information
        for li in bin_dates_div.find_all("li", {"class": "text-large"}):
            # Extract bin type from the span tag
            bin_type_span = li.find("span", {"class": "font-weight-bold"})
            if not bin_type_span:
                continue
            
            bin_type = bin_type_span.get_text(strip=True)
            
            # Extract collection date from the strong tag
            date_strong = li.find("strong")
            if not date_strong:
                continue
            
            date_text = date_strong.get_text(strip=True)
            
            try:
                # Parse date in format "Monday, 2 February 2026"
                collection_date = datetime.strptime(date_text, "%A, %d %B %Y")
                
                # Get the full bin description (e.g., "Black (Residual waste)")
                # Extract text between bin type and " bin on"
                full_text = li.get_text(strip=True)
                # Pattern: "Black (Residual waste) bin on Monday, 2 February 2026"
                match = re.search(rf"{re.escape(bin_type)}\s+(.*?)\s+bin on", full_text)
                if match:
                    bin_description = match.group(1).strip()
                    if bin_description:
                        bin_type = f"{bin_type} {bin_description}"
                
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )
            except ValueError:
                # Skip if date parsing fails
                continue

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
