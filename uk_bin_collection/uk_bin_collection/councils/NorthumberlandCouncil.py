import datetime
import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def extract_styles(self, style_str: str) -> dict:
        return dict(
            (a.strip(), b.strip())
            for a, b in (
                element.split(":") for element in style_str.split(";") if element
            )
        )

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
<<<<<<< HEAD
            # Use the new URL as mentioned in the issue
            page = "http://bincollection.northumberland.gov.uk"
=======
            page = "https://bincollection.northumberland.gov.uk/postcode"
>>>>>>> master

            data = {"bins": []}

            user_postcode = kwargs.get("postcode")
            user_uprn = kwargs.get("uprn")

            check_postcode(user_postcode)
            check_uprn(user_uprn)

            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            # Create wait object
            wait = WebDriverWait(driver, 20)

<<<<<<< HEAD
            # The new site may have different structure, so we'll need to adapt
            # Try to find postcode and house number inputs
            try:
                # Look for postcode input field
                postcode_input = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//input[contains(@name, 'postcode') or contains(@id, 'postcode') or contains(@placeholder, 'postcode')]")
                    )
                )

                # Look for house number input field
                house_input = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//input[contains(@name, 'house') or contains(@id, 'house') or contains(@name, 'number') or contains(@placeholder, 'house')]")
                    )
                )

                # Enter details
                postcode_input.send_keys(user_postcode)
                house_input.send_keys(user_paon)

                # Look for submit button
                submit_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[@type='submit'] | //input[@type='submit'] | //button[contains(text(), 'Search')] | //input[contains(@value, 'Search')]")
                    )
                )
                submit_button.click()

                # Wait for results to load
                time.sleep(3)

                # Get page source after everything has loaded
                soup = BeautifulSoup(driver.page_source, features="html.parser")

                # Look for collection dates and bin types in the results
                # This is a generic approach that looks for common patterns
                import re
                from datetime import datetime

                # Look for date patterns in the page
                date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4}\b'
                page_text = soup.get_text()
                dates = re.findall(date_pattern, page_text, re.IGNORECASE)

                # Look for bin type keywords near dates
                bin_keywords = ['recycling', 'refuse', 'garden', 'waste', 'rubbish', 'general', 'household']

                # Try to extract structured data from tables or lists
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            # Look for date in first cell and bin type in second
                            date_text = cells[0].get_text().strip()
                            type_text = cells[1].get_text().strip()

                            # Try to parse date
                            try:
                                if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', date_text):
                                    date_obj = datetime.strptime(date_text, '%d/%m/%Y')
                                elif re.match(r'\d{1,2}\s+\w+\s+\d{4}', date_text):
                                    date_obj = datetime.strptime(date_text, '%d %B %Y')
                                else:
                                    continue

                                if any(keyword in type_text.lower() for keyword in bin_keywords):
                                    data["bins"].append({
                                        "type": type_text,
                                        "collectionDate": date_obj.strftime(date_format)
                                    })
                            except ValueError:
                                continue

            except TimeoutException:
                # If the new site structure is completely different, fall back to old URL
                driver.get("https://www.northumberland.gov.uk/Waste/Household-waste/Household-bin-collections/Bin-Calendars.aspx")

                # Wait for and click cookie button if present
                try:
                    cookie_button = wait.until(
                        EC.element_to_be_clickable((By.ID, "ccc-notify-accept"))
                    )
                    cookie_button.click()
                except TimeoutException:
                    pass

                # Continue with original logic for old site
                inputElement_hn = wait.until(
                    EC.presence_of_element_located(
                        (
                            By.ID,
                            "p_lt_ctl04_pageplaceholder_p_lt_ctl02_WasteCollectionCalendars_NCCAddressLookup_txtHouse",
                        )
                    )
                )

                inputElement_pc = wait.until(
                    EC.presence_of_element_located(
                        (
                            By.ID,
                            "p_lt_ctl04_pageplaceholder_p_lt_ctl02_WasteCollectionCalendars_NCCAddressLookup_txtPostcode",
                        )
                    )
                )

                inputElement_pc.send_keys(user_postcode)
                inputElement_hn.send_keys(user_paon)

                lookup_button = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.ID,
                            "p_lt_ctl04_pageplaceholder_p_lt_ctl02_WasteCollectionCalendars_NCCAddressLookup_butLookup",
                        )
                    )
                )
                lookup_button.click()

                route_summary = wait.until(
                    EC.presence_of_element_located(
                        (
                            By.ID,
                            "p_lt_ctl04_pageplaceholder_p_lt_ctl02_WasteCollectionCalendars_spanRouteSummary",
                        )
                    )
                )

                soup = BeautifulSoup(driver.page_source, features="html.parser")

                bins_collected = list(
                    map(
                        str.strip,
                        soup.find(
                            "span",
                            id="p_lt_ctl04_pageplaceholder_p_lt_ctl02_WasteCollectionCalendars_spanRouteSummary",
                        )
                        .text.replace("Routes found: ", "")
                        .split(","),
                    )
                )

                bins_by_colours = dict()
                for bin in bins_collected:
                    if "(but no dates found)" in bin:
                        continue
                    style_str = soup.find("span", string=bin)["style"]
                    bin_colour = self.extract_styles(style_str)["background-color"].upper()
                    bins_by_colours[bin_colour] = bin

                calander_tables = soup.find_all("table", title="Calendar")
                for table in calander_tables:
                    rows = table.find_all("tr")
                    month_and_year = (
                        rows[0].find("table", class_="calCtrlTitle").find("td").string
                    )
                    bin_days = table.find_all("td", class_="calCtrlDay")
                    for day in bin_days:
                        day_styles = self.extract_styles(day["style"])
                        if "background-color" in day_styles:
                            colour = day_styles["background-color"].upper()
                            date = time.strptime(
                                f"{day.string} {month_and_year}", "%d %B %Y"
                            )

                            data["bins"].append(
                                {
                                    "type": bins_by_colours[colour],
                                    "collectionDate": time.strftime(date_format, date),
                                }
                            )

=======
            # Wait for and click cookie button
            cookie_button = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "accept-all"))
            )
            cookie_button.click()

            # Wait for and find postcode input
            inputElement_pc = wait.until(
                EC.presence_of_element_located((By.ID, "postcode"))
            )

            # Enter postcode and submit
            inputElement_pc.send_keys(user_postcode)
            submit_button = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "govuk-button"))
            )
            submit_button.click()

            # Wait for and find house number input
            selectElement_address = wait.until(
                EC.presence_of_element_located((By.ID, "address"))
            )

            dropdown = Select(selectElement_address)
            dropdown.select_by_value(user_uprn)

            # Click submit button and wait for results
            submit_button = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "govuk-button"))
            )
            submit_button.click()

            # Wait for results to load
            route_summary = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "govuk-table"))
            )

            now = datetime.now()
            current_month = now.month
            current_year = now.year

            # Get page source after everything has loaded
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # From the table, find all rows:
            # - cell 1 is the date in format eg. 9 September (so no year value 🥲)
            # - cell 2 is the day name, not useful
            # - cell 3 is the bin type eg. "General waste", "Recycling", "Garden waste"
            rows = soup.find("tbody", class_="govuk-table__body").find_all(
                "tr", class_="govuk-table__row"
            )

            for row in rows:
                bin_type = row.find_all("td")[-1].text.strip()

                collection_date_string = row.find("th").text.strip()

                # sometimes but not always the day is written "22nd" instead of 22 so make sure we get a proper int
                collection_date_day = "".join(
                    [
                        i
                        for i in list(collection_date_string.split(" ")[0])
                        if i.isdigit()
                    ]
                )
                collection_date_month_name = collection_date_string.split(" ")[1]

                # if we are currently in Oct, Nov, or Dec and the collection month is Jan, Feb, or Mar, let's assume its next year
                if (current_month >= 10) and (
                    collection_date_month_name in ["January", "February", "March"]
                ):
                    collection_date_year = current_year + 1
                else:
                    collection_date_year = current_year

                collection_date = time.strptime(
                    f"{collection_date_day} {collection_date_month_name} {collection_date_year}",
                    "%d %B %Y",
                )

                # Add it to the data
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": time.strftime(date_format, collection_date),
                    }
                )
>>>>>>> master
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data
