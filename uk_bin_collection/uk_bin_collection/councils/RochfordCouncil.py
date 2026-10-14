import re

from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from dateutil.relativedelta import relativedelta
from datetime import timedelta

LOOKUP_URL = "https://www.rochford.gov.uk/bins-and-collections"
AJAX_URL = f"{LOOKUP_URL}?ajax_form=1&_wrapper_format=drupal_ajax"
LEGACY_CALENDAR_URL = "https://www.rochford.gov.uk/online-bin-collections-calendar"
FORM_ID = "waste_collection_block_ajax_form"
AJAX_WRAPPER = "#waste-collection-ajax-wrapper"


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.

    Rochford supports two modes:

    * Postcode lookup (preferred): uses the "Bin Collection Day" tool on
      https://www.rochford.gov.uk/bins-and-collections to return exact
      collection dates for a specific address. Requires a postcode plus a
      house number/name (``paon``) or UPRN to pick the address.
    * Legacy calendar: if no postcode is supplied, falls back to parsing the
      district-wide online calendar, which only publishes "week commencing"
      date ranges. Kept so existing configurations continue to work.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        """Parse bin collection data for Rochford Council.

        If a postcode is provided, uses the exact online address lookup.
        Otherwise falls back to the legacy calendar parser for backwards
        compatibility with older configurations.
        """
        user_postcode = kwargs.get("postcode")
        if user_postcode:
            return self._parse_postcode_lookup(
                user_postcode,
                paon=kwargs.get("paon"),
                uprn=kwargs.get("uprn"),
            )

        # Backwards compatibility: older configs only stored the calendar URL
        # and rely on the framework fetching it for us. If we've been called
        # with skip_get_url (so no page was fetched), fetch it ourselves.
        url = kwargs.get("url") or LEGACY_CALENDAR_URL
        if "online-bin-collections-calendar" not in url:
            url = LEGACY_CALENDAR_URL
            page = None
        if not hasattr(page, "text"):
            page = self.get_data(url)
        return self._parse_legacy_calendar(page)

    # ------------------------------------------------------------------ #
    # Postcode lookup (Drupal AJAX "waste_collection_block_ajax_form")
    # ------------------------------------------------------------------ #
    @staticmethod
    def _ajax_insert_html(response) -> str:
        """Return the HTML Drupal inserts into the waste collection wrapper."""
        response.raise_for_status()
        for command in response.json():
            if (
                command.get("command") == "insert"
                and command.get("selector") == AJAX_WRAPPER
                and isinstance(command.get("data"), str)
            ):
                return command["data"]
        raise ValueError(
            "Unexpected response from Rochford bin lookup. "
            "The page structure may have changed."
        )

    @staticmethod
    def _match_address(options: list, paon=None, uprn=None) -> str:
        """Pick an address option value matching the given UPRN or PAON.

        Option values look like "<ward code>-<UPRN>", e.g. "E05010853-100090593697".
        """
        if uprn:
            uprn_norm = str(uprn).strip().lstrip("0")
            for value, _ in options:
                if value.rsplit("-", 1)[-1].lstrip("0") == uprn_norm:
                    return value

        if paon:
            paon_norm = str(paon).strip().upper()
            # 1. Exact leading match with comma or space (e.g. "19, ..." or "19 ...")
            for value, label in options:
                label_up = label.upper()
                if label_up.startswith(paon_norm + ",") or label_up.startswith(
                    paon_norm + " "
                ):
                    return value

            # 2. Match exact word boundary of paon at start of address
            pattern = re.compile(rf"^{re.escape(paon_norm)}($|[\s,])")
            for value, label in options:
                if pattern.search(label.upper()):
                    return value

            # 3. Match all PAON tokens while ignoring punctuation
            paon_tokens = re.findall(r"\w+", paon_norm)
            if len(paon_tokens) > 1:
                for value, label in options:
                    label_tokens = re.findall(r"\w+", label.upper())
                    if label_tokens[: len(paon_tokens)] == paon_tokens:
                        return value

        if not uprn and not paon and len(options) == 1:
            return options[0][0]

        available = "; ".join(label for _, label in options)
        raise ValueError(
            f"Could not match address (house number={paon!r}, uprn={uprn!r}). "
            f"Available addresses: {available}"
        )

    def _parse_postcode_lookup(self, postcode: str, paon=None, uprn=None) -> dict:
        """Query the Drupal AJAX form by postcode and retrieve exact collection dates."""
        session = build_retry_session(headers={"User-Agent": get_scraper_user_agent()})
        ajax_headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
        }

        # Step 0: fetch the page to get a form_build_id token
        response = session.get(LOOKUP_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, features="html.parser")
        build_id_input = soup.select_one(
            "form#waste-collection-block-ajax-form input[name=form_build_id]"
        )
        if not build_id_input:
            raise ValueError("Could not find the bin lookup form on Rochford page")

        # Step 1: submit the postcode to get the list of addresses
        response = session.post(
            AJAX_URL,
            data={
                "postcode": postcode,
                "form_build_id": build_id_input["value"],
                "form_id": FORM_ID,
                "_triggering_element_name": "op",
                "_triggering_element_value": "Find",
            },
            headers=ajax_headers,
            timeout=30,
        )
        fragment = BeautifulSoup(
            self._ajax_insert_html(response), features="html.parser"
        )
        options = [
            (opt["value"], opt.get_text(strip=True))
            for opt in fragment.select("select[name=uprn] option")
            if opt.get("value")
        ]
        if not options:
            message = fragment.get_text(" ", strip=True)
            raise ValueError(f"No addresses found for postcode {postcode}: {message}")

        build_id_input = fragment.find("input", {"name": "form_build_id"})
        if not build_id_input:
            raise ValueError("Could not find form_build_id in address results")

        address_value = self._match_address(options, paon=paon, uprn=uprn)

        # Step 2: submit the selected address to get the collection schedule
        response = session.post(
            AJAX_URL,
            data={
                "uprn": address_value,
                "form_build_id": build_id_input["value"],
                "form_id": FORM_ID,
                "_triggering_element_name": "op",
                "_triggering_element_value": "View collection days",
            },
            headers=ajax_headers,
            timeout=30,
        )
        schedule = BeautifulSoup(
            self._ajax_insert_html(response), features="html.parser"
        )

        # Rows look like:
        # <tr class="govuk-table__row waste-collection__day">
        #   <td class="waste-collection__day--day"><time datetime="2026-10-15">15</time></td>
        #   <td class="waste-collection__day--type">Garden Waste</td>
        #   <td class="waste-collection__day--colour">Green Bin</td>
        # </tr>
        # Note: the month <table>s are not closed properly in the source HTML,
        # so select rows globally rather than walking table by table.
        today = datetime.now().date()
        collections = []
        for row in schedule.select("tr.waste-collection__day"):
            time_el = row.find("time")
            type_el = row.find(class_="waste-collection__day--type")
            if not time_el or not time_el.get("datetime") or not type_el:
                continue

            collection_date = datetime.strptime(time_el["datetime"], "%Y-%m-%d")
            if collection_date.date() < today:
                continue

            # Direct text only, in case a nested note (e.g. bank holiday
            # notice) is ever added inside the type cell.
            bin_type = type_el.find(text=True, recursive=False)
            bin_type = (bin_type or type_el.get_text()).strip()
            if not bin_type:
                continue

            colour_el = row.find(class_="waste-collection__day--colour")
            bin_colour = colour_el.get_text(strip=True) if colour_el else ""
            if bin_colour:
                bin_type = f"{bin_type} ({bin_colour})"

            collections.append((bin_type, collection_date))

        if not collections:
            raise ValueError(
                "No collection dates found for the selected Rochford address"
            )

        collections.sort(key=lambda item: item[1])
        return {
            "bins": [
                {"type": bin_type, "collectionDate": date.strftime(date_format)}
                for bin_type, date in collections
            ]
        }

    # ------------------------------------------------------------------ #
    # Legacy district-wide calendar ("week commencing" ranges)
    # ------------------------------------------------------------------ #
    def _parse_legacy_calendar(self, page) -> dict:
        """Parse the district-wide calendar page with 'week commencing' dates."""
        data = {"bins": []}

        # response = requests.get('https://www.rochford.gov.uk/online-bin-collections-calendar', headers=headers)
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()
        year = soup.find_all("table", {"class": "responsive-enabled govuk-table"})

        current_month = datetime.now().strftime("%B %Y")
        next_month = (datetime.now() + relativedelta(months=1, day=1)).strftime("%B %Y")

        for month in year:
            heading = (
                month.find("th", {"class": "govuk-table__header"}).get_text().strip()
            )
            if heading == current_month or heading == next_month:
                for week in month.find("tbody").find_all(
                    "tr", {"class": "govuk-table__row"}
                ):
                    week_text = week.get_text().strip().split("\n")
                    # The site publishes a date *range* for the collection
                    # week (e.g. "Monday 6th July - Friday 10th July"), not
                    # the resident's actual collection day. Take the last
                    # (latest) date in the range rather than the first, so a
                    # week isn't treated as "already passed" - and therefore
                    # skipped ahead to the next occurrence - as soon as its
                    # Monday goes by, even though the real collection day
                    # (any day up to Friday) hasn't happened yet.
                    date_parts = re.split(r"\s*[-–�]\s*", week_text[0])
                    date_str = date_parts[-1].strip()
                    collection_date = datetime.strptime(
                        remove_ordinal_indicator_from_date_string(date_str),
                        "%A %d %B",
                    )
                    next_collection = collection_date.replace(year=datetime.now().year)
                    if datetime.now().month == 12 and next_collection.month == 1:
                        next_collection = next_collection + relativedelta(years=1)
                    bin_type = (
                        week_text[1]
                        .replace("collection week", "bin")
                        .strip()
                        .capitalize()
                    )
                    if next_collection.date() >= (datetime.now().date() - timedelta(6)):
                        dict_data = {
                            "type": bin_type,
                            "collectionDate": next_collection.strftime(date_format),
                        }
                        data["bins"].append(dict_data)
            else:
                continue

        return data
