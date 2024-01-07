import json
from collections import OrderedDict
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
import ssl
import urllib3
import logging


class CustomHttpAdapter(requests.adapters.HTTPAdapter):
    """Transport adapter" that allows us to use custom ssl_context."""

    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=self.ssl_context,
        )


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Make a BS4 object

        driver = None
        try:
            data = {"bins": []}
            uprn = kwargs.get("uprn")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            current_month = datetime.today().strftime("%m")
            current_year = datetime.today().strftime("%Y")
            url = (
                f"https://mybins.blackburn.gov.uk/api/mybins/getbincollectiondays?uprn={uprn}&month={current_month}"
                f"&year={current_year}"
            )
            driver = create_webdriver(web_driver, headless)
            driver.get(url)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Find the <pre> tag that contains the JSON data
            pre_tag = soup.find("pre")

            if pre_tag:
                # Extract the text content within the <pre> tag

                # Return JSON from response and loop through collections
                json_result = json.loads(pre_tag.contents[0])
                bin_collections = json_result["BinCollectionDays"]
                for collection in bin_collections:
                    if collection is not None:
                        bin_type = collection[0].get("BinType")
                        current_collection_date = datetime.strptime(
                            collection[0].get("CollectionDate"), "%Y-%m-%d"
                        )
                        next_collection_date = datetime.strptime(
                            collection[0].get("NextScheduledCollectionDate"), "%Y-%m-%d"
                        )

                        # Work out the most recent collection date to display
                        if (
                            datetime.today().date()
                            <= current_collection_date.date()
                            < next_collection_date.date()
                        ):
                            collection_date = current_collection_date
                        else:
                            collection_date = next_collection_date

                        dict_data = {
                            "type": bin_type,
                            "collectionDate": collection_date.strftime(date_format),
                        }
                        data["bins"].append(dict_data)

                        data["bins"].sort(
                            key=lambda x: datetime.strptime(
                                x.get("collectionDate"), date_format
                            )
                        )
        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return data
