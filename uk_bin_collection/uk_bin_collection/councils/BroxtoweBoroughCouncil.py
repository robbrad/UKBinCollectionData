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

    def _dump_options(self, select_obj) -> None:
        """Diagnostic only: print every <option>'s value/text/selected
        state in an address dropdown, to discover the real value format
        this rebuilt form uses (previous code assumed "U"+UPRN, which
        was specific to the old ASP.NET page and can no longer be
        assumed). Remove once #2188 is fixed for real."""
        try:
            print(f"[diagnostic] dropdown has {len(select_obj.options)} options")
            for option in select_obj.options:
                print(
                    "[diagnostic] option",
                    "value=" + repr(option.get_attribute("value")),
                    "text=" + repr(option.text),
                    "selected=" + repr(option.is_selected()),
                )
        except Exception as exc:
            print(f"[diagnostic] failed to enumerate dropdown options: {exc}")

    def _dump_form_fields(self, driver) -> None:
        """Diagnostic only: print the page's current URL/title and every
        input/select/button/textarea/form element's tag, id, name, type,
        and class. Not covered by unit tests; remove once #2188 is fixed
        for real against the live page."""
        try:
            print(f"[diagnostic] current_url: {driver.current_url!r}")
            print(f"[diagnostic] title: {driver.title!r}")
            elements = driver.find_elements(
                By.CSS_SELECTOR, "input, select, button, textarea, form"
            )
            print(f"[diagnostic] found {len(elements)} candidate elements")
            for element in elements:
                print(
                    "[diagnostic]",
                    element.tag_name,
                    "id=" + repr(element.get_attribute("id")),
                    "name=" + repr(element.get_attribute("name")),
                    "type=" + repr(element.get_attribute("type")),
                    "class=" + repr(element.get_attribute("class")),
                )
        except Exception as exc:
            print(f"[diagnostic] failed to enumerate page elements: {exc}")

        try:
            form = driver.find_element(By.ID, "edit-item")
            print(f"[diagnostic] form visible text:\n{form.text}")
        except Exception as exc:
            print(f"[diagnostic] failed to read form text: {exc}")

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            page = "https://selfservice.broxtowe.gov.uk/renderform.aspx?t=217&k=9D2EF214E144EE796430597FB475C3892C43C528"

            data = {"bins": []}

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

            # The council rebuilt this form (confirmed live: the old
            # ctl00_ContentPlaceHolder1_FF5683* ASP.NET WebForms ids are
            # gone; the page now redirects renderform.aspx -> renderform
            # and uses semantic ids like FF5683-text/-find/-list). The
            # field number (5683) is the same, only the id scheme changed.

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
            # populate - the <select> itself renders before the address
            # options are filled in asynchronously after the search click.
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

            # DIAGNOSTIC: the old code assumed option values were "U"+UPRN,
            # which was specific to the old page. Dump the real value/text
            # format so the real matching logic can be written from data.
            self._dump_options(dropdownSelect)

            # Each option's value is "U<uprn>|<full address text>" - match
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
                    f"Address not found for UPRN '{user_uprn}' or house number in "
                    "dropdown (see [diagnostic] option dump above for the real format)"
                )

            # Wait for the submit button to appear, then click it to get the collection dates
            submit = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "submit-button"))
            )
            submit.click()

            # This form re-renders its section via JS rather than a full
            # page navigation, so the previous section's elements (e.g.
            # the dropdown) go stale rather than the URL changing. Wait
            # for that staleness before reading the DOM again, instead of
            # racing the transition.
            try:
                WebDriverWait(driver, 15).until(EC.staleness_of(dropdown))
            except TimeoutException:
                pass

            # DIAGNOSTIC: the results container's id isn't known yet
            # (this is a different page state than the initial dump). Dump
            # it before we know what to look for.
            self._dump_form_fields(driver)
            raise ValueError(
                "[diagnostic] stopping deliberately after submit - see the "
                "[diagnostic] dumps above for the real results container"
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            bins_div = soup.find("div", id=results_id)
            if bins_div:
                bins_table = bins_div.find("table")
                if bins_table:
                    # Get table rows
                    for row in bins_table.find_all("tr"):
                        # Get the rows cells
                        cells = row.find_all("td")
                        bin_type = cells[0].get_text(strip=True)
                        # Skip header row
                        if bin_type and cells[3] and bin_type != "Bin Type":
                            if len(cells[3].get_text(strip=True)) > 0:
                                collection_date = datetime.strptime(
                                    cells[3].get_text(strip=True), "%A, %d %B %Y"
                                )
                                dict_data = {
                                    "type": bin_type,
                                    "collectionDate": collection_date.strftime(
                                        date_format
                                    ),
                                }
                                data["bins"].append(dict_data)

                            data["bins"].sort(
                                key=lambda x: datetime.strptime(
                                    x.get("collectionDate"), "%d/%m/%Y"
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
