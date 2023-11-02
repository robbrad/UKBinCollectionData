import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber


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
        page = "https://www.northumberland.gov.uk/Waste/Bins/Bin-Calendars.aspx"

        data = {"bins": []}

        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        check_paon(user_paon)
        check_postcode(user_postcode)

        # Create Selenium webdriver
        driver = create_webdriver(web_driver)
        driver.get(page)

        time.sleep(1)

        # Press the cookie accept - wait is to let the JS load it up
        driver.find_element(By.ID, "ccc-notify-accept").click()

        inputElement_hn = driver.find_element(
            By.ID,
            "p_lt_ctl04_pageplaceholder_p_lt_ctl02_WasteCollectionCalendars_NCCAddressLookup_txtHouse",
        )
        inputElement_pc = driver.find_element(
            By.ID,
            "p_lt_ctl04_pageplaceholder_p_lt_ctl02_WasteCollectionCalendars_NCCAddressLookup_txtPostcode",
        )

        inputElement_pc.send_keys(user_postcode)
        inputElement_hn.send_keys(user_paon)

        driver.find_element(
            By.ID,
            "p_lt_ctl04_pageplaceholder_p_lt_ctl02_WasteCollectionCalendars_NCCAddressLookup_butLookup",
        ).click()

        soup = BeautifulSoup(driver.page_source, features="html.parser")

        # Work out which bins can be collected for this address. Glass bins are only on some houses due to pilot programme.
        bins_collected = list(
            map(
                str.strip,
                soup.find(
                    "span",
                    id="p_lt_ctl04_pageplaceholder_p_lt_ctl02_WasteCollectionCalendars_spanRouteSummary",
                )
                .string.replace("Routes found: ", "")
                .split(","),
            )
        )

        # Get the background colour for each of them...
        bins_by_colours = dict()
        for bin in bins_collected:
            style_str = soup.find("span", string=bin)["style"]
            bin_colour = self.extract_styles(style_str)["background-color"].upper()
            bins_by_colours[bin_colour] = bin

        # Work through the tables gathering the dates, if the cell has a background colour - match it to the bin type.
        calander_tables = soup.find_all("table", title="Calendar")
        for table in calander_tables:
            # Get month and year
            # First row in table is the header
            rows = table.find_all("tr")
            month_and_year = (
                rows[0].find("table", class_="calCtrlTitle").find("td").string
            )
            bin_days = table.find_all("td", class_="calCtrlDay")
            for day in bin_days:
                day_styles = self.extract_styles(day["style"])
                if "background-color" in day_styles:
                    colour = day_styles["background-color"].upper()
                    date = time.strptime(f"{day.string} {month_and_year}", "%d %B %Y")

                    # Add it to the data
                    data["bins"].append(
                        {
                            "type": bins_by_colours[colour],
                            "collectionDate": time.strftime(date_format, date),
                        }
                    )

        return data
