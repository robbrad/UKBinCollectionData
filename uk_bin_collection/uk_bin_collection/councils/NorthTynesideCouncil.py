import logging
from datetime import datetime
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import check_uprn, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

logger = logging.getLogger(__name__)


class CouncilClass(AbstractGetBinDataClass):
    """
    North Tyneside Council bin collection schedule parser
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        """
        Parse waste collection schedule data for a given UPRN.

        Args:
            page (str): Unused parameter (required by parent class interface).
            **kwargs: Keyword arguments containing:
                - uprn (str): The Unique Property Reference Number for the property.

        Returns:
            dict: A dictionary containing:
                - bins (list): A list of dictionaries, each containing:
                    - type (str): Bin type and colour in format "Type (Colour)"
                                 (e.g., "Recycling (Grey)")
                    - collectionDate (str): Collection date in the format specified
                                           by date_format

        Raises:
            ValueError: If no waste collection schedule is found on the page, indicating
                       the page structure may have changed.
            requests.HTTPError: If the HTTP request to fetch the schedule fails.

        Notes:
            - The method handles bank holiday notifications that may appear in the
              collection type field, extracting only the direct text content.
            - Invalid or unparsable collection entries are logged and skipped.
            - Results are sorted by collection date in ascending order.
        """
        # `page` is unused because we construct the view URL directly.
        del page

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        # Fetch the schedule page (includes UA, verify=False, timeout)
        view_url = f"https://www.northtyneside.gov.uk/waste-collection-schedule/view/{user_uprn}"
        response = self.get_data(view_url)

        # Fail fast on HTTP errors
        if getattr(response, "raise_for_status", None):
            response.raise_for_status()


        # Parse form page and get the day of week and week offsets
        soup = BeautifulSoup(response.text, features="html.parser")
        schedule = soup.find("div", {"class": "waste-collection__schedule"})

        if schedule is None:
            raise ValueError("No waste-collection schedule found. The page structure may have changed.")


        # Find days of form:
        #
        # <li class="waste-collection__day">
        #   <span class="waste-collection__day--day"><time datetime="2025-11-13">13</time></span>
        #   <span class="waste-collection__day--type">Recycling</span>
        #   <span class="waste-collection__day--colour waste-collection__day--grey">Grey</span>
        # </li>
        #
        #
        # Note that on back holidays the collection type is of form:
        # ...
        # <span class="waste-collection__day--type">Recycling
        #    <span>
        #      Public holiday - services may be affected. Check service updates on <a href="/household-rubbish-and-recycling/household-bin-collections/bank-holiday-bin-collections">our website</a>
        #    </span>
        # </span>
        # ...

        collections = []

        for day in schedule.find_all("li", {"class": "waste-collection__day"}):
            try:
                time_el = day.find("time")
                if not time_el or not time_el.get("datetime"):
                    logger.warning("Skipping day: missing time/datetime")
                    continue
                collection_date = datetime.strptime(time_el["datetime"], "%Y-%m-%d")

                type_span = day.find("span", {"class": "waste-collection__day--type"})
                # Direct text only (exclude nested spans, e.g., bank-holiday note)
                bin_type_text = type_span.find(text=True, recursive=False) if type_span else None
                if not bin_type_text:
                    logger.warning("Skipping day: missing type")
                    continue
                bin_type = bin_type_text.strip()

                colour_span = day.find("span", {"class": "waste-collection__day--colour"})
                if not colour_span:
                    logger.warning("Skipping day: missing colour")
                    continue
                bin_colour = colour_span.get_text(strip=True)

                collections.append((f"{bin_type} ({bin_colour})", collection_date))
            except (AttributeError, KeyError, TypeError, ValueError) as e:
                logger.warning(f"Skipping unparsable day node: {e}")
                continue

        return {
            "bins": [
                {
                    "type": item[0],
                    "collectionDate": item[1].strftime(date_format),
                }
                for item in sorted(collections, key=lambda x: x[1])
            ]
        }
