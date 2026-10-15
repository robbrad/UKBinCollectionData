"""City of Doncaster Council bin collections.

Doncaster retired its Compass waste portal during 2026. The endpoint this
scraper used to call, ``/Compass/PremiseDetail/GetCollectionsForCalendar``,
now redirects to an ASP.NET error page that is served with HTTP 200, so the
old status-code guard let an HTML body through to ``json.loads``. The council
publishes collection dates through a Netcall Liberty Create app instead, which
is searched by postcode and property rather than by UPRN.
"""

import json
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import (
    check_postcode,
    create_webdriver,
    date_format,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

SEARCH_PAGE = "https://doncaster-wasterecycling.oncreate.app/w/webpage/bin-query"

# Liberty Create builds the form field ids out of its own page and field
# references, so they change whenever the council rebuilds the app. The labels
# a visitor reads are stable, so each input is found through the label that
# points at it rather than by position in the form.
POSTCODE_INPUT = (
    "//input[@type='text']"
    "[@id=//label[contains(normalize-space(.), 'Postcode')]/@for]"
)
PROPERTY_INPUT = (
    "//input[@type='text']"
    "[@id=//label[contains(normalize-space(.), 'Property')]/@for]"
)
SEARCH_BUTTON = ".system_widget_search input[type='submit']"
RESULTS_TABLE = ".system_widget_foundation_listing table"
ADDRESS_LINK = "a.webpage_link"
ADDRESS_LINK_PROMPT = "View collection details"

# The calendar is a Vue/FullCalendar widget, and Liberty Create hands it the
# whole event list up front in the widget container's data-params, so every
# published date is there without paging the calendar a month at a time. The
# rendered grid is only read as a fallback, and holds a single month.
CALENDAR_WIDGET = "div.system_widget_code_studio_fixed[data-params]"
CALENDAR_DAY = "td.fc-daygrid-day[data-date]"
CALENDAR_EVENT_TITLE = ".fc-event-title"

# Shown in place of the calendar for a property that is not on a domestic
# round, which covers every council building and shop tried on the live app.
NO_COLLECTIONS_MESSAGE = "no collection information available"


class CouncilClass(AbstractGetBinDataClass):
    @staticmethod
    def _parse_iso_date(value: str):
        """Return a date for an ISO day, or None when it cannot be read."""
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except (AttributeError, ValueError):
            return None

    def _events_from_widget_params(self, soup) -> list:
        """Read the calendar's own event list out of the widget's data-params."""
        events = []
        for widget in soup.select(CALENDAR_WIDGET):
            try:
                params = json.loads(widget["data-params"])
            except ValueError:
                continue
            template_data = params.get("template_data")
            if not isinstance(template_data, dict):
                continue
            for event in template_data.get("events") or []:
                bin_type = (event.get("title") or "").strip()
                collection_date = self._parse_iso_date(event.get("date") or "")
                if bin_type and collection_date:
                    events.append((collection_date, bin_type))
        return events

    def _events_from_calendar_grid(self, soup) -> list:
        """Fall back to whichever month the calendar has already rendered."""
        events = []
        for day in soup.select(CALENDAR_DAY):
            collection_date = self._parse_iso_date(day["data-date"])
            if collection_date is None:
                continue
            for title in day.select(CALENDAR_EVENT_TITLE):
                bin_type = title.get_text(strip=True)
                if bin_type:
                    events.append((collection_date, bin_type))
        return events

    def _parse_collections(self, page: str) -> dict:
        """Extract every published collection from an address's calendar page."""
        soup = BeautifulSoup(page, "html.parser")
        events = self._events_from_widget_params(
            soup
        ) or self._events_from_calendar_grid(soup)

        if not events:
            if NO_COLLECTIONS_MESSAGE in soup.get_text(" ", strip=True).lower():
                raise ValueError(
                    "The council holds no collection information for this address. "
                    f"Check the address on {SEARCH_PAGE}."
                )
            raise ValueError(
                "No collection calendar was found for this address. The council's "
                "waste app may have changed."
            )

        # Sorting the set puts the collections in date order and drops the
        # duplicate the calendar carries when a service is listed twice.
        return {
            "bins": [
                {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format),
                }
                for collection_date, bin_type in sorted(set(events))
            ]
        }

    @staticmethod
    def _address_of(link) -> str:
        """Read a result row's address off its collection details link."""
        label = link.get_attribute("aria-label") or link.get_attribute("textContent")
        label = (label or "").replace(ADDRESS_LINK_PROMPT, " ")
        return " ".join(label.replace(",", " ").split())

    @staticmethod
    def _match_score(address: str, paon: str) -> int:
        """Score a result row against the requested house number or name.

        Matching is done on whole words so that a request for "3" is not
        answered with "13", and the leading words of the address are preferred
        so that "23" picks "23 Station Road" over "Rear Of 23 Station Road".
        """
        wanted = " ".join(paon.replace(",", " ").split()).lower().split()
        found = address.lower().split()
        if not wanted:
            return 0
        if found[: len(wanted)] == wanted:
            return 2
        for start in range(1, len(found) - len(wanted) + 1):
            if found[start : start + len(wanted)] == wanted:
                return 1
        return 0

    def _best_match(self, links: list, paon: str):
        """Return the result row that best matches the requested property."""
        scored = [
            (self._match_score(self._address_of(link), paon), link) for link in links
        ]
        scored = [pair for pair in scored if pair[0]]
        if not scored:
            return None
        return max(scored, key=lambda pair: pair[0])[1]

    def wait_for_element_conditions(self, driver, conditions, timeout: int = 20):
        """Wait for a Selenium condition, propagating a timeout if it fails."""
        try:
            WebDriverWait(driver, timeout).until(conditions)
        except TimeoutException:
            print("Timed out waiting for the council's page to load")
            raise

    def _run_address_search(self, driver, postcode: str, paon) -> list:
        """Search the app for a postcode, narrowed by property when given."""
        driver.get(SEARCH_PAGE)
        self.wait_for_element_conditions(
            driver, EC.presence_of_element_located((By.XPATH, POSTCODE_INPUT))
        )

        postcode_input = driver.find_element(By.XPATH, POSTCODE_INPUT)
        postcode_input.clear()
        postcode_input.send_keys(postcode)

        # The search remembers the criteria it was last given for the session,
        # so the property field is always written to, even to empty it.
        property_input = driver.find_element(By.XPATH, PROPERTY_INPUT)
        property_input.clear()
        if paon:
            property_input.send_keys(paon)

        # The results of the previous search are still on the page when it is
        # loaded a second time, so wait for the submit to navigate away before
        # looking for the table, rather than reading the stale one.
        search_button = driver.find_element(By.CSS_SELECTOR, SEARCH_BUTTON)
        search_url = driver.current_url
        search_button.click()
        self.wait_for_element_conditions(
            driver,
            EC.any_of(
                EC.staleness_of(search_button),
                lambda submitted: submitted.current_url != search_url,
            ),
        )
        self.wait_for_element_conditions(
            driver, EC.presence_of_element_located((By.CSS_SELECTOR, RESULTS_TABLE))
        )
        return driver.find_elements(By.CSS_SELECTOR, ADDRESS_LINK)

    def _select_address(self, driver, postcode: str, paon: str) -> None:
        """Find the requested address and open its collection calendar."""
        links = self._run_address_search(driver, postcode, paon)
        match = self._best_match(links, paon)

        if match is None:
            # The property box is a plain substring search against the
            # council's own record, so a house name written differently finds
            # nothing at all. Ask again for the whole postcode and match here.
            links = self._run_address_search(driver, postcode, None)
            match = self._best_match(links, paon)

        if match is None:
            found = ", ".join(self._address_of(link) for link in links[:10])
            raise ValueError(
                f"No address matching '{paon}' was found in {postcode}. "
                f"Addresses found: {found or 'none'}."
            )

        driver.get(match.get_attribute("href"))
        self.wait_for_element_conditions(
            driver,
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, CALENDAR_WIDGET)),
                EC.presence_of_element_located(
                    (By.XPATH, f"//*[contains(text(), '{NO_COLLECTIONS_MESSAGE}')]")
                ),
            ),
        )

    def parse_data(self, page: str, **kwargs) -> dict:
        """Look up a postcode and property, returning their collection dates."""
        driver = None
        try:
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")

            check_postcode(user_postcode)
            if not user_paon:
                raise ValueError(
                    "A house number or name is needed to pick an address out of "
                    "the council's postcode search."
                )

            # No User-Agent is forced on the driver. The app has no bot
            # management of its own, and a hardcoded string would claim an OS
            # and a Chrome version that the browser's own JavaScript then
            # contradicts, which is what trips Cloudflare on other councils.
            driver = create_webdriver(web_driver, headless, None, __name__)
            self._select_address(driver, user_postcode, user_paon)
            data = self._parse_collections(driver.page_source)
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data
