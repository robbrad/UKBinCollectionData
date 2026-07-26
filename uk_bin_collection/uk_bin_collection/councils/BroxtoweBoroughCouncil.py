from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def _parse_collection_table(self, soup: BeautifulSoup) -> dict:
        """Parse the "Premises Collections" table: Bin Type / Collection
        Day / Last Collection / Next Collection."""
        data = {"bins": []}

        table = soup.find("table")
        if not table:
            return data

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            bin_type = cells[0].get_text(strip=True)
            if not bin_type or bin_type == "Bin Type":
                continue

            date_text = cells[3].get_text(strip=True)
            if not date_text:
                continue

            collection_date = datetime.strptime(date_text, "%A, %d %B %Y")
            data["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format),
                }
            )

        data["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )
        return data

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            page = "https://selfservice.broxtowe.gov.uk/renderform.aspx?t=217&k=9D2EF214E144EE796430597FB475C3892C43C528"

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(page)

            # The council rebuilt this form on a new platform (confirmed
            # live): the old ctl00_ContentPlaceHolder1_FF5683* ASP.NET
            # WebForms ids are gone, renderform.aspx now redirects to
            # renderform, and fields use semantic ids instead. The field
            # number (5683) is unchanged, only the id scheme is.

            # Populate postcode field
            inputElement_postcode = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "FF5683-text"))
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "FF5683-find"))
            ).click()

            # Wait for the 'Select address' dropdown to appear AND actually
            # populate - the <select> renders before its <option>s are
            # filled in asynchronously after the search click.
            def _populated_select(d):
                try:
                    select_el = d.find_element(By.ID, "FF5683-list")
                except Exception:
                    return False
                return (
                    select_el
                    if len(select_el.find_elements(By.TAG_NAME, "option")) > 1
                    else False
                )

            dropdown = WebDriverWait(driver, 15).until(_populated_select)
            dropdownSelect = Select(dropdown)

            # Each option's value is "U<uprn>|<full address text>". Match
            # on the value's UPRN prefix first, falling back to matching
            # the visible text against the house number/name.
            matched = False
            if user_uprn:
                target_prefix = f"u{user_uprn}|"
                for option in dropdownSelect.options:
                    value = (option.get_attribute("value") or "").strip().lower()
                    if value.startswith(target_prefix):
                        option.click()
                        matched = True
                        break

            if not matched:
                user_paon = kwargs.get("paon") or ""
                paon_lower = user_paon.strip().lower()
                for option in dropdownSelect.options:
                    text = option.text.strip().lower()
                    if (
                        text
                        and paon_lower
                        and (
                            text.startswith(paon_lower + " ")
                            or text.startswith(paon_lower + ",")
                        )
                    ):
                        option.click()
                        matched = True
                        break

            if not matched:
                raise ValueError(
                    f"Address not found for UPRN '{user_uprn}' or house number in dropdown"
                )

            # Submit the address selection.
            submit = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "submit-button"))
            )
            submit.click()

            # This form re-renders its section via JS rather than a full
            # page navigation, so the previous section's elements (e.g.
            # the dropdown) go stale rather than the URL changing. Wait for
            # that staleness, then for the results table, instead of
            # racing the transition.
            try:
                WebDriverWait(driver, 15).until(EC.staleness_of(dropdown))
            except TimeoutException:
                pass

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            data = self._parse_collection_table(soup)
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
