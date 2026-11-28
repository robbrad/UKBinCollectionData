from uk_bin_collection.uk_bin_collection.common import create_webdriver
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from uk_bin_collection.uk_bin_collection.salesforce_property_flow import (
    build_bins,
    fetch_collection_rows,
)

URL = "https://community.fdean.gov.uk/s/waste-collection-enquiry"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)


class CouncilClass(AbstractGetBinDataClass):
    """Forest of Dean: Salesforce waste collection enquiry (see salesforce_property_flow)."""

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = create_webdriver(
            kwargs.get("web_driver"), kwargs.get("headless"), USER_AGENT, __name__
        )
        try:
            rows = fetch_collection_rows(
                driver, URL, kwargs.get("paon"), kwargs.get("postcode")
            )
        finally:
            driver.quit()
        return build_bins(rows)
