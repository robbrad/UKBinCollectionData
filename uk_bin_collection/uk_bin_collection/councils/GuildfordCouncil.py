import time

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import create_webdriver
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from uk_bin_collection.uk_bin_collection.salesforce_property_flow import (
    build_bins,
    run_in_page,
    select_address_option,
)

URL = "https://my.guildford.gov.uk/customers/s/view-bin-collections"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)
WAIT_SECONDS = 120


class CouncilClass(AbstractGetBinDataClass):
    """Guildford: Salesforce portal; driven in page JS, see salesforce_property_flow."""

    def parse_data(self, page: str, **kwargs) -> dict:
        postcode = kwargs.get("postcode")
        house_number = kwargs.get("paon")
        if not postcode or not house_number:
            raise ValueError("Both a house number/name and a postcode are required")

        driver = create_webdriver(
            kwargs.get("web_driver"), kwargs.get("headless"), USER_AGENT, __name__
        )
        try:
            driver.get(URL)
            wait = WebDriverWait(driver, WAIT_SECONDS)
            wait.until(
                lambda d: run_in_page(d, "return deep('input.slds-input').length > 0")
            )
            run_in_page(
                driver, "const i = deep('input.slds-input')[0]; i.focus(); i.click();"
            )
            ActionChains(driver).send_keys(postcode).perform()
            if not run_in_page(driver, "return deep('input.slds-input')[0].value"):
                raise RuntimeError("The postcode box did not keep the typed text")
            run_in_page(
                driver,
                """
                deep('button')
                    .find(b => b.innerText.trim() === 'Find address').click();
                """,
            )

            address_script = """
                return deep('input[type=radio]').map(
                    r => r.closest('tr').innerText.trim().split('\\n').pop());
            """
            wait.until(lambda d: run_in_page(d, address_script))
            addresses = run_in_page(driver, address_script)
            options = [
                {"address": address, "value": index}
                for index, address in enumerate(addresses)
            ]
            chosen = select_address_option(options, house_number, postcode)
            run_in_page(
                driver,
                "deep('input[type=radio]')[arguments[0]].click();",
                chosen["value"],
            )
            if not run_in_page(
                driver,
                "return deep('input[type=radio]')[arguments[0]].checked;",
                chosen["value"],
            ):
                raise RuntimeError(f"Could not select the address {chosen['address']}")
            run_in_page(driver, "deep('button[name=NEXT]')[0].click();")

            rows_script = """
                return deep('tr.slds-hint-parent').map(r => {
                    const job = r.querySelector('td[data-label="Bin Job"]');
                    const next = r.querySelector('td[data-label="Next Collection"]');
                    if (!job || !next) return null;
                    const strong = job.querySelector('strong');
                    return [(strong || job).innerText.trim(), next.innerText.trim()];
                }).filter(row => row);
            """
            deadline = time.monotonic() + WAIT_SECONDS
            rows = []
            while not rows and time.monotonic() < deadline:
                rows = run_in_page(driver, rows_script)
                if not rows:
                    time.sleep(1)
            if not rows:
                raise TimeoutError("No bin collection table appeared")
        finally:
            driver.quit()
        return build_bins([(bin_type, day) for bin_type, day in rows])
