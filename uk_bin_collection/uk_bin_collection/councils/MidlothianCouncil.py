from urllib.parse import quote, urljoin

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

    BASE_URL = "https://www.midlothian.gov.uk"
    DIRECTORY_URL = f"{BASE_URL}/site/scripts/directory_search.php?directoryID=35&keywords={{}}&search=Search"
    BIN_TYPES = {
        "Next recycling collection": "Recycling",
        "Next grey bin collection": "Grey Bin",
        "Next brown bin collection": "Brown Bin",
        "Next food bin collection": "Food Bin",
    }

    def parse_data(self, page: str, **kwargs) -> dict:

        house_identifier = kwargs.get(
            "paon", ""
        ).strip()  # Could be house number or name
        postcode = kwargs.get("postcode")

        # Check if both house identifier and postcode are provided
        if not house_identifier:
            print("Error: House identifier (number or name) must be provided.")
            return {"bins": []}

        if not postcode:
            print("Error: Postcode must be provided.")
            return {"bins": []}

        check_postcode(postcode)
        check_paon(house_identifier)

        data = {"bins": []}
        search_url = self.DIRECTORY_URL.format(quote(postcode))

        try:
            search_results_html = requests.get(search_url)
            search_results_html.raise_for_status()

            soup = BeautifulSoup(search_results_html.text, "html.parser")
            address_link = self._get_result_by_identifier(soup, house_identifier)

            if address_link:
                collections_url = urljoin(search_url, address_link["href"])
                bin_collection_data = self._fetch_bin_collection_data(collections_url)

                if bin_collection_data:
                    data["bins"].extend(bin_collection_data)

        except requests.RequestException as e:
            print(
                f"Warning: Failed to fetch data from {postcode_search_url}. Error: {e}"
            )

        return data

    def _get_result_by_identifier(self, soup, identifier: str) -> list:
        """Extract the result link that matches the given house number or house name."""
        try:
            results_list = (
                soup.find("article", class_="container")
                .find("h2", text="Search results")
                .find_next("ul", class_="item-list item-list__rich")
            )

            pattern = re.compile(re.escape(identifier.lower()) + r"[ ,]")

            for item in results_list.find_all("li"):
                address_link = item.find("a")
                if address_link:
                    link_text = address_link.text.strip().lower()
                    if pattern.match(link_text):
                        return address_link

            print(f"Warning: No results found for identifier '{identifier}'.")
            return None  # Return None if no match is found

        except AttributeError as e:
            print(f"Warning: Could not find the search results. Error: {e}")
            return None  # Return None if no result found

    def _fetch_bin_collection_data(self, url: str) -> list:
        """Fetch and parse bin collection data from the given URL."""
        try:
            bin_collection_html = requests.get(url)
            bin_collection_html.raise_for_status()

            soup = BeautifulSoup(bin_collection_html.text, "html.parser")
            bin_collections = soup.find("ul", class_="data-table")

            if bin_collections:
                return self._parse_bin_collection_items(
                    bin_collections.find_all("li")[2:]  # Skip the first two items
                )

        except requests.RequestException as e:
            print(
                f"Warning: Failed to fetch bin collection data from {url}. Error: {e}"
            )

        return []  # Return an empty list on error

    def _parse_bin_collection_items(self, bin_items: list) -> list:
        """Parse bin collection items into a structured format."""
        parsed_bins = []

        for bin_item in bin_items:
            bin_type = None
            try:
                if bin_item.h2 and bin_item.h2.text.strip() in self.BIN_TYPES:
                    bin_type = self.BIN_TYPES[bin_item.h2.text.strip()]

                bin_collection_date = None
                if bin_item.div and bin_item.div.text.strip():
                    try:
                        bin_collection_date = datetime.strptime(
                            bin_item.div.text.strip(), "%A %d/%m/%Y"
                        ).strftime(date_format)
                    except ValueError:
                        print(
                            f"Warning: Date parsing failed for {bin_item.div.text.strip()}."
                        )

                if bin_type and bin_collection_date:
                    parsed_bins.append(
                        {
                            "type": bin_type,
                            "collectionDate": bin_collection_date,
                        }
                    )
                else:
                    print(f"Warning: Missing data for bin item: {bin_item}")

            except Exception as e:
                print(f"Warning: An error occurred while parsing bin item. Error: {e}")

        return parsed_bins
