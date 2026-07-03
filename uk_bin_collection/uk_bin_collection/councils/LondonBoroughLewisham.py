import html

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://lewisham.gov.uk"
COLLECTION_PAGE_URL = (
    f"{BASE_URL}/myservices/recycling-and-rubbish/your-bins/collection"
)
ROUNDS_INFORMATION_PATH = "/api/roundsinformation"
# Identifies the "rounds information" widget on the collection page in Lewisham's
# CMS (Sitecore). The site's JS calls this same endpoint+id to render the
# schedule text, so we call it directly instead of driving a browser.
ROUNDS_INFORMATION_ITEM_GUID = "{23423835-d2a6-41b1-9637-29e5e8cc2df7}"

_DAY_PATTERN = re.compile(
    r"on\s*(?P<day>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
    re.IGNORECASE,
)
_NEXT_DATE_PATTERN = re.compile(
    r"your\s+next\s+collection\s+date\s+is\s*(?P<date>\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        if not user_uprn:
            raise ValueError(
                "Could not resolve UPRN. Provide a valid UPRN, e.g. via FindMyAddress."
            )

        session = build_retry_session(
            headers={
                "User-Agent": get_scraper_user_agent(),
                "Accept": "application/json, text/html, */*",
                "Accept-Language": "en-GB,en;q=0.9",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": COLLECTION_PAGE_URL,
            },
            retry_methods=("POST",),
        )

        resp = session.post(
            f"{BASE_URL}{ROUNDS_INFORMATION_PATH}",
            params={"item": ROUNDS_INFORMATION_ITEM_GUID, "uprn": user_uprn},
            timeout=30,
        )
        resp.raise_for_status()

        # The API response body is itself a JSON string containing an HTML fragment,
        # e.g. "<strong>Food waste</strong>&nbsp;is collected <span ...>WEEKLY</span>
        # on Thursday...". json.loads unwraps that outer string; html.unescape then
        # decodes entities like &nbsp; so the regexes below can match plain text.
        try:
            raw_html = json.loads(resp.text)
        except json.JSONDecodeError as ex:
            raise ValueError(
                "Unexpected response from Lewisham roundsinformation API (not JSON)."
            ) from ex

        normalised = html.unescape(raw_html).replace("\xa0", " ")
        soup = BeautifulSoup(normalised, "html.parser")

        # Each bin type is a <strong> tag; the day/frequency/date for that bin
        # follows as plain text and <span> markup up until the next <strong> tag.
        strong_tags = soup.find_all("strong")
        if not strong_tags:
            raise ValueError("No collection entries found for this UPRN.")

        bindata = {"bins": []}
        for strong in strong_tags:
            bin_type = strong.get_text(strip=True)

            segment = ""
            for sibling in strong.next_siblings:
                if getattr(sibling, "name", None) == "strong":
                    break
                # Tags have get_text(); loose text nodes (NavigableString) don't.
                segment += (
                    sibling.get_text() if hasattr(sibling, "get_text") else str(sibling)
                )

            date_match = _NEXT_DATE_PATTERN.search(segment)
            day_match = _DAY_PATTERN.search(segment)

            if date_match:
                # An explicit "your next collection date is dd/mm/yyyy" was given.
                next_collection_date = date_match.group("date")
            elif day_match:
                # No explicit date (e.g. fortnightly collections without one) -
                # fall back to the next occurrence of the named weekday. .title()
                # normalises case, since get_next_day_of_week does an exact match.
                next_collection_date = get_next_day_of_week(
                    day_match.group("day").title(), date_format
                )
            else:
                raise ValueError(
                    f"Could not determine a collection day or date for '{bin_type}'."
                )

            bindata["bins"].append(
                {"type": bin_type, "collectionDate": next_collection_date}
            )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )
        return bindata
