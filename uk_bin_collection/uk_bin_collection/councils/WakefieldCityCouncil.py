from bs4 import BeautifulSoup
from selenium import webdriver
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Set up Selenium to run 'headless'
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Create Selenium webdriver
        driver = webdriver.Chrome(options=options)
        driver.get(kwargs.get("url"))

        # Make a BS4 object
        soup = BeautifulSoup(driver.page_source, features="html.parser")
        soup.prettify()

        data = {"bins": []}
        sections = soup.find_all("div", {"class": "wil_c-content-section_heading"})
        for s in sections:
            if s.get_text(strip=True).lower() == "bin collections":
                rows = s.find_next_sibling("div", {"class": "c-content-section_body"}).find_all(
                    "div", {"class": "u-mb-8"}
                )
                for row in rows:
                    title = row.find("div", {"class": "u-mb-4"})
                    collections = row.find_all("div", {"class": "u-mb-2"})
                    if title and collections:
                        for c in collections:
                            if c.get_text(strip=True).lower().startswith('next collection'):
                                # add next collection
                                next_collection_date = datetime.strptime(
                                    c.get_text(strip=True).replace('Next collection - ', ''),
                                    "%A, %d %B %Y",
                                ).strftime(date_format)
                                dict_data = {
                                    "type": title.get_text(strip=True).capitalize(),
                                    "collectionDate": next_collection_date,
                                }
                                data["bins"].append(dict_data)
                                # add future collections without duplicating next collection
                                future_collections = row.find("ul", {"class": "u-mt-4"}).find_all("li")
                                for c in future_collections:
                                    future_collection_date = datetime.strptime(
                                        c.get_text(strip=True),
                                        "%A, %d %B %Y",
                                    ).strftime(date_format)
                                    if future_collection_date != next_collection_date:
                                        dict_data = {
                                            "type": title.get_text(strip=True).capitalize(),
                                            "collectionDate": future_collection_date,
                                        }
                                        data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
