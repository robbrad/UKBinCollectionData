from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# The council's own site embedded a "Bin collection calendar" iframe that
# has since been replaced with a link out to a WhiteSpace Work and Resource
# Planning portal (the same platform several other councils in this repo
# already use, e.g. WaverleyBoroughCouncil) - no Selenium needed.
BASE_URL = "https://nimea-wrp.whitespacews.com/"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Origin": "https://nimea-wrp.whitespacews.com",
}


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)
        check_paon(user_paon)

        session = requests.Session()

        # Starting the form generates a one-time "Track" id in the URL of
        # the "View my collections" link - every subsequent request needs it.
        start_response = session.get(BASE_URL, timeout=30)
        start_soup = BeautifulSoup(start_response.content, features="html.parser")
        start_link = start_soup.find(
            "a", string=lambda t: t and "View my collections" in t
        )
        if not start_link:
            raise ValueError("Could not find the collections form start link")
        track_id = parse_qs(urlparse(start_link["href"]).query)["Track"][0]

        headers = {**_HEADERS, "Referer": start_link["href"]}
        form_data = {
            "address_name_number": user_paon,
            "address_street": "",
            "street_town": "",
            "address_postcode": user_postcode,
        }
        search_url = f"{BASE_URL}mop.php?serviceID=A&Track={track_id}&seq=2"
        search_response = session.post(
            search_url, headers=headers, data=form_data, timeout=30
        )
        search_soup = BeautifulSoup(search_response.content, features="html.parser")

        candidates = search_soup.find_all("a", class_="app-subnav__link")
        paon_upper = user_paon.strip().upper()
        address_link = next(
            (
                a
                for a in candidates
                if a.get("aria-label", "").upper().startswith(paon_upper + ",")
            ),
            candidates[0] if len(candidates) == 1 else None,
        )
        if not address_link:
            raise ValueError(
                f"No address found for postcode {user_postcode} and house "
                f"number/name {user_paon}"
            )

        collections_url = BASE_URL + address_link["href"]
        collections_response = session.get(
            collections_url, headers={**_HEADERS, "Referer": search_url}, timeout=30
        )
        collections_soup = BeautifulSoup(
            collections_response.content, features="html.parser"
        )

        ul_blocks = collections_soup.find_all(
            "ul",
            {
                "class": "displayinlineblock justifycontentleft alignitemscenter margin0 padding0"
            },
        )
        for ul in ul_blocks:
            li_items = ul.find_all_next(
                "li", {"class": "displayinlineblock padding0px20px5px0px"}
            )
            # Each entry is 3 <li> - blank, date, bin type.
            for i in range(0, len(li_items) - 2, 3):
                date_text = li_items[i + 1].text.strip()
                bin_type = li_items[i + 2].text.strip()
                if not date_text or not bin_type:
                    continue
                try:
                    collection_date = datetime.strptime(
                        date_text, date_format
                    ).strftime(date_format)
                except ValueError:
                    continue
                data["bins"].append(
                    {"type": bin_type, "collectionDate": collection_date}
                )
            break

        return data
