import re
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# aria-label example: "Organic Begin From Wednesday, July 1, 2026 at 12:00:00 AM ..."
APPOINTMENT_LABEL_RE = re.compile(r"^(.+?) Begin From \w+, (\w+ \d{1,2}, \d{4})")


class CouncilClass(AbstractGetBinDataClass):
    """
    Staffordshire Moorlands District Council moved from the old
    FindYourBinDay form to the same Syncfusion-based "Public Dashboard"
    platform (bins.staffsmoorlands.gov.uk) that High Peak Borough Council
    also migrated to, which shows collections as calendar appointments
    for a selected premises.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            user_postcode = kwargs.get("postcode")
            user_uprn = kwargs.get("uprn")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            check_postcode(user_postcode)

            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get("https://bins.staffsmoorlands.gov.uk/PublicDashboard")

            wait = WebDriverWait(driver, 20)

            postcode_input = wait.until(
                EC.presence_of_element_located((By.ID, "SelectedPostcode"))
            )
            postcode_input.send_keys(user_postcode)

            driver.find_element(
                By.CSS_SELECTOR, 'button[formaction*="handler=SearchPostcode"]'
            ).click()

            # The premises dropdown is a Syncfusion combobox - it must be
            # opened before its option list is rendered into the DOM.
            wait.until(EC.presence_of_element_located((By.ID, "Premises")))
            # The dropdown's wrapper span is the actual designed click
            # target and overlaps the readonly input itself.
            premises_wrapper = driver.find_element(
                By.CSS_SELECTOR, 'span[aria-labelledby="Premises_hidden"]'
            )
            premises_wrapper.click()

            wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.e-list-item"))
            )

            options = driver.find_elements(By.CSS_SELECTOR, "li.e-list-item")
            selected_option = None
            if user_uprn:
                for option in options:
                    if option.get_attribute("data-value") == str(user_uprn):
                        selected_option = option
                        break
            if not selected_option:
                selected_option = options[0]
            selected_option.click()

            driver.find_element(
                By.CSS_SELECTOR, 'button[formaction*="handler=SelectPrem"]'
            ).click()

            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "e-appointment")))

            data = {"bins": []}
            today = datetime.now().date()
            for appointment in driver.find_elements(By.CLASS_NAME, "e-appointment"):
                label = appointment.get_attribute("aria-label") or ""
                match = APPOINTMENT_LABEL_RE.match(label)
                if not match:
                    continue
                bin_type, date_str = match.groups()
                collection_date = datetime.strptime(date_str, "%B %d, %Y")
                if collection_date.date() < today:
                    continue
                data["bins"].append(
                    {
                        "type": bin_type.strip(),
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )

            data["bins"].sort(
                key=lambda x: datetime.strptime(x["collectionDate"], date_format)
            )
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data
