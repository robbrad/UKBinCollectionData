from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from datetime import datetime


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete class to scrape bin collection data.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            # Create Selenium webdriver
            headless = kwargs.get("headless")
            driver = create_webdriver(
                kwargs.get("web_driver"), headless, None, __name__
            )
            driver.get(kwargs.get("url"))

            # Make a BS4 object
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            data = {"bins": []}
            # Locate the section with bin collection data
            sections = soup.find_all("div", {"class": "wil_c-content-section_heading"})

            for s in sections:
                if s.get_text(strip=True).lower() == "bin collections":
                    rows = s.find_next_sibling(
                        "div", {"class": "c-content-section_body"}
                    ).find_all("div", class_="tablet:l-col-fb-4 u-mt-10")

                    for row in rows:
                        title_elem = row.find("div", class_="u-mb-4")
                        if title_elem:
                            title = title_elem.get_text(strip=True).capitalize()

                            # Find all collection info in the same section
                            collections = row.find_all("div", class_="u-mb-2")
                            for c in collections:
                                text = c.get_text(strip=True).lower()

                                if "next collection" in text:
                                    date_text = text.replace("next collection - ", "")
                                    try:
                                        next_collection_date = datetime.strptime(
                                            date_text, "%A, %d %B %Y"
                                        ).strftime(date_format)

                                        dict_data = {
                                            "type": title,
                                            "collectionDate": next_collection_date,
                                        }
                                        data["bins"].append(dict_data)
                                    except ValueError:
                                        # Skip if the date isn't a valid date
                                        print(f"Skipping invalid date: {date_text}")

                            # Get future collections
                            future_collections_section = row.find("ul", class_="u-mt-4")
                            if future_collections_section:
                                future_collections = (
                                    future_collections_section.find_all("li")
                                )
                                for future_collection in future_collections:
                                    future_date_text = future_collection.get_text(
                                        strip=True
                                    )
                                    try:
                                        future_collection_date = datetime.strptime(
                                            future_date_text, "%A, %d %B %Y"
                                        ).strftime(date_format)

                                        # Avoid duplicates of next collection date
                                        if (
                                            future_collection_date
                                            != next_collection_date
                                        ):
                                            dict_data = {
                                                "type": title,
                                                "collectionDate": future_collection_date,
                                            }
                                            data["bins"].append(dict_data)
                                    except ValueError:
                                        # Skip if the future collection date isn't valid
                                        print(
                                            f"Skipping invalid future date: {future_date_text}"
                                        )

            # Sort the collections by date
            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
            )
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data
