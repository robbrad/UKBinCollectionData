import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)
        check_paon(user_paon)
        bindata = {"bins": []}

        base_url = "https://collectiondates.eastlothian.gov.uk/waste-collection-schedule"
        headers = {
            "User-Agent": "Mozilla/5.0",
        }

        session = requests.Session()

        # Step 1: GET the page to obtain session cookie and form_build_id
        response = session.get(base_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        form_build_id = soup.find("input", {"name": "form_build_id"})
        if not form_build_id:
            raise ValueError("Could not find form_build_id on initial page")

        # Step 2: POST postcode to get address list
        response = session.post(
            base_url,
            headers=headers,
            data={
                "postcode": user_postcode,
                "op": "Find",
                "form_build_id": form_build_id["value"],
                "form_id": "localgov_waste_collection_postcode_form",
            },
            allow_redirects=True,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Find matching address by house number
        select = soup.find("select", {"name": "uprn"})
        if not select:
            raise ValueError(f"No addresses found for postcode {user_postcode}")

        # Normalise user input: strip spaces, lowercase for comparison
        # Council formats as "87 B" but user may pass "87b" or "87B"
        norm_paon = user_paon.replace(" ", "").lower()

        uprn = None
        for option in select.find_all("option"):
            if not option.get("value"):
                continue
            addr_text = option.text.strip()
            addr_parts = addr_text.split()
            candidate = ""
            for i, part in enumerate(addr_parts):
                candidate += part.lower()
                if candidate == norm_paon:
                    # If the next part is a single letter (sub-unit suffix like "B"),
                    # keep accumulating — "87" should not match "87 B ..."
                    if i + 1 < len(addr_parts):
                        next_part = addr_parts[i + 1]
                        if len(next_part) == 1 and next_part.isalpha():
                            continue
                    uprn = option["value"]
                    break
            if uprn:
                break

        if not uprn:
            raise ValueError(
                f"Address '{user_paon}' not found for postcode {user_postcode}"
            )

        # Get the form action URL and new form_build_id
        form = soup.find(
            "form", {"id": "localgov-waste-collection-address-select-form"}
        )
        if not form:
            raise ValueError("Could not find address select form")

        action_url = form.get("action", "")
        if action_url.startswith("/"):
            action_url = "https://collectiondates.eastlothian.gov.uk" + action_url

        form_build_id = form.find("input", {"name": "form_build_id"})
        if not form_build_id:
            raise ValueError("Could not find form_build_id in address form")

        # Step 3: POST selected UPRN to get collection schedule
        response = session.post(
            action_url,
            headers=headers,
            data={
                "uprn": uprn,
                "op": "Find",
                "form_build_id": form_build_id["value"],
                "form_id": "localgov_waste_collection_address_select_form",
            },
            allow_redirects=True,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Parse collection dates from <time datetime="YYYY-MM-DD"> elements
        days = soup.find_all("li", class_="waste-collection__day")
        for day in days:
            time_el = day.find("time")
            type_el = day.find("span", class_="waste-collection__day--type")

            if not time_el or not type_el:
                continue

            date_str = time_el.get("datetime", "")
            waste_type = type_el.text.strip()

            if not date_str or not waste_type:
                continue

            try:
                collection_date = datetime.strptime(date_str, "%Y-%m-%d")
                bindata["bins"].append(
                    {
                        "type": waste_type,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )
            except ValueError:
                continue

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
