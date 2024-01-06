from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dateutil.parser import parse

from uk_bin_collection.uk_bin_collection.common import create_webdriver, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def wait_for_element(self, driver, element_type, element: str, timeout: int = 5):
        element_present = EC.presence_of_element_located((element_type, element))
        self.wait_for_element_conditions(driver, element_present, timeout=timeout)

    def wait_for_element_conditions(self, driver, conditions, timeout: int = 5):
        try:
            WebDriverWait(driver, timeout).until(conditions)
        except TimeoutException:
            print("Timed out waiting for page to load")
            raise

    def parse_data(self, page: str, **kwargs) -> dict:
        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")
        page = "https://westsuffolk-self.achieveservice.com/service/WSS_EX_Inf_Bin_Collection_Postcode_Lookup"

        # Assign user info
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")

        # Create Selenium webdriver
        driver = create_webdriver(web_driver, headless)
        driver.get(page)

        # Click the cookie button
        css_selector = "#close-cookie-message"
        self.wait_for_element(driver, By.CSS_SELECTOR, css_selector)
        cookie_button = driver.find_element(By.CSS_SELECTOR, css_selector)
        cookie_button.click()

        # switch to the form iframe
        iframe = driver.find_element(By.CSS_SELECTOR, "#fillform-frame-1")
        driver.switch_to.frame(iframe)

        # Wait for form to load
        xpath_selector = '//*[@id="postcode_search"]'
        self.wait_for_element(driver, By.XPATH, xpath_selector, timeout=6)

        # Send postcode
        postcode_input_box = driver.find_element(By.XPATH, xpath_selector)
        postcode_input_box.send_keys(user_postcode)
        postcode_input_box.send_keys(Keys.ENTER)

        search_for_address_button = driver.find_element(
            By.CSS_SELECTOR, "#addresssearch"
        )
        search_for_address_button.click()

        # Find address
        self.wait_for_element(
            driver, By.CSS_SELECTOR, "#selectaddr > option:nth-child(2)"
        )
        select_address_dropdown = Select(
            driver.find_element(By.CSS_SELECTOR, "#selectaddr")
        )
        if user_paon is not None:
            for option in select_address_dropdown.options:
                if user_paon in option.text:
                    select_address_dropdown.select_by_visible_text(option.text)
                    break
        else:
            # If we've not been supplied an address, pick the second entry
            select_address_dropdown.select_by_index(1)

        # Click the get schedule button (Once it's available)
        self.wait_for_element_conditions(
            driver,
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#searchforcollections")),
        )
        check_schedules_button = driver.find_element(
            By.CSS_SELECTOR, "#searchforcollections"
        )
        check_schedules_button.click()

        # Grab the bin output data
        # Span is of the format:
        #   Your Next bin collections are:
        #   Black bin - Wednesday 29th November
        #    Blue bin - Wednesday 6th December
        #    Brown bin - Wednesday 6th December
        output_span_css_selector = "//span[@data-name='statictext6']"
        output_span_ec = EC.all_of(
            EC.presence_of_element_located((By.XPATH, output_span_css_selector)),
            EC.text_to_be_present_in_element(
                (By.XPATH, output_span_css_selector), "bin collections"
            ),
        )
        self.wait_for_element_conditions(driver, output_span_ec)
        data_span = driver.find_element(By.XPATH, output_span_css_selector)

        data = {"bins": []}
        for item in data_span.text.splitlines():
            if "bin" in item and " - " in item:
                bin_data = item.split(" - ")
                bin_name = bin_data[0]
                bin_date = bin_data[1]
                parsed_bin_date = parse(bin_date, fuzzy_with_tokens=True)[0]

                dict_data = {
                    "type": bin_name,
                    "collectionDate": parsed_bin_date.strftime(date_format),
                }

                data["bins"].append(dict_data)

        # Quit Selenium webdriver to release session
        driver.quit()

        return data
