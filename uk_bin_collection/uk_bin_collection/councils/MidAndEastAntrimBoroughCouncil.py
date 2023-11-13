from bs4 import BeautifulSoup
import time
from dateutil.relativedelta import relativedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
     AbstractGetBinDataClass

class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        page = "https://www.midandeastantrim.gov.uk/resident/waste-recycling/collection-dates/"

        # Assign user info
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        web_driver = kwargs.get("web_driver")

        # Create Selenium webdriver
        options = webdriver.ChromeOptions()
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = create_webdriver(web_driver)
        
        driver.get(page)

        time.sleep(5)
        number=0
        driver.switch_to.frame(number)
        # Enter postcode in text box and wait
        inputElement_pc = driver.find_element(
            By.ID, "txtAjaxSearch"
        )
        inputElement_pc.send_keys(user_postcode)

        time.sleep(5)

        # Submit address information and wait - selecting the top one only
        # if it is an exact match then it will go straight to the results
        try:
            button = driver.find_element(
                By.XPATH, '//*[@id="show-button-0"]'
            )
            driver.execute_script("arguments[0].click();", button)
        except NoSuchElementException:
            pass

        time.sleep(4)

        # Read next collection information
        page = driver.find_element(
            By.ID, "divCalendarGraphics"
        ).get_attribute("outerHTML")
        
        # Make a BS4 object - remove bold tags and add @ so we can split the lines later
        soup = BeautifulSoup(page.strip().replace("<b>", "").replace("</b>", "").replace("<br>", "@"), features="html.parser")
        soup.prettify()

        # Data to return
        data = {"bins": []}

        # Valid bin types
        binTypes = [
            "Refuse",
            "Garden"
        ]

        # Value to create dict for bin values
        keys, values = [], []

        # Loop though html for text containing bins
        # example of html (bold tags removed above)
        # <div id="divCalendarGraphics">
        # <br>  <b>Refuse</b>: Tue 14 Nov then every alternate  Tue<br><b>Recycling</b>: No Recycling waste collection for this address<br><b>Garden</b>: Tue 21 Nov then every alternate  Tue<br><img src="img/Gif-Spacer.gif" alt="spacer" height="1" width="30">
        # split by br tag and take first 4 splits
        lines = soup.text.split('@',4)
        for line in lines[1:4]:
            keys.append(line.split(':')[0].strip())
            # strip out the day and month from the text
            values.append(line.split(':')[1].strip().split(' ')[:3])

        # Create dict for bin name and string dates
        binDict = dict(zip(keys, values))

        # Process dict for valid bin types
        for bin in list(binDict):
            if bin in binTypes:
                # Convert date - no year value so take it from todays date
                if binDict[bin][0] == "Tomorrow":
                    date = datetime.today() + relativedelta(days=1)
                elif binDict[bin][0] == "Today":
                    date = datetime.today()
                else:
                    date = datetime.strptime(' '.join(binDict[bin][1:]), "%d %b").replace(year=datetime.today().year)
                    # if the date is in the past then it means the collection is next year so add a year
                    if date < datetime.today():
                        date = date + relativedelta(years=1)

                # Set bin data
                dict_data = {
                    "type": bin,
                    "collectionDate": date.strftime(date_format),
                }
                data["bins"].append(dict_data)

        # Quit Selenium webdriver to release session
        driver.quit()

        return data
