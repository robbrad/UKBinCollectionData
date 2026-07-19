"""Bin collection scraper for Durham County Council."""

import logging
import re
import warnings
from datetime import datetime

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

_LOGGER = logging.getLogger(__name__)


class CouncilClass(AbstractGetBinDataClass):
    """Scraper for Durham County Council bin collection data.

    Durham's public bin lookup page (durham.gov.uk/bincollections) is
    rendered client-side from a JSON-RPC endpoint. This scraper bypasses
    the rendered page and calls the JSON-RPC backend directly, parsing
    the XML payload it returns.

    The `page` argument to `parse_data` is unused; `input.json` sets
    `skip_get_url=true` for this council so no upstream GET is made.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        """Fetch and parse upcoming bin collections for a Durham UPRN.

        Args:
            page: Unused. Required by the abstract base class signature
                but ignored here — see class docstring.
            **kwargs: Must contain `uprn` (Unique Property Reference
                Number) identifying the property to look up.

        Returns:
            A dict in the project's standard schema:
            ``{"bins": [{"type": str, "collectionDate": str}, ...]}``
            where `collectionDate` is formatted per `common.date_format`
            and only the next upcoming collection per bin type is
            included.

        Raises:
            ValueError: If the JSON-RPC endpoint returns an error
                response or an unexpected payload shape.
        """
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        response = requests.post(
            "https://www.durham.gov.uk/apiserver/ajaxlibrary/",
            json={
                "jsonrpc": "2.0",
                "method": "durham.Localities.GetBartecCalendar",
                "params": {"uprn": uprn},
                "id": "21",
                "name": "V2 AJAX End Point Library Worker",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise ValueError(f"Durham JSON-RPC error: {payload['error']}")
        xml_string = payload.get("result")
        if not isinstance(xml_string, str):
            raise ValueError("Unexpected Durham JSON-RPC response: missing result")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
            soup = BeautifulSoup(xml_string, "html.parser")

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Optional "Empty Bin " prefix, capture bin label, optional " 240L"
        # volume suffix. Whitespace is flexible throughout. fullmatch() is
        # used so unexpected leading/trailing content surfaces as a warning
        # rather than being silently absorbed.
        name_pattern = re.compile(r"(?:Empty\s+Bin\s+)?(.+?)(?:\s+\d+\s*[Ll])?")

        next_dates = {}
        for job in soup.find_all("job"):
            name_tag = job.find("name")
            start_tag = job.find("scheduledstart")
            if not name_tag or not start_tag:
                continue

            raw_name = name_tag.get_text(strip=True)
            match = name_pattern.fullmatch(raw_name)
            if not match:
                _LOGGER.warning("Could not parse a collection type")
                continue
            label = match.group(1).strip()

            try:
                scheduled = datetime.strptime(
                    start_tag.get_text(strip=True)[:10], "%Y-%m-%d"
                )
            except ValueError:
                _LOGGER.warning("Could not parse a scheduled collection date")
                continue

            if scheduled < today:
                continue
            if label not in next_dates or scheduled < next_dates[label]:
                next_dates[label] = scheduled

        data = {"bins": []}
        for bin_type, collection_date in next_dates.items():
            data["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format),
                }
            )

        return data
