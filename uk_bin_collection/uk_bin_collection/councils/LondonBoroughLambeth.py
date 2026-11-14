import requests
from requests.structures import CaseInsensitiveDict

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

ADDRESS_SEARCH_URL = "https://wasteservice.lambeth.gov.uk/LLPG/addressSearch"


def match_address(options, paon):
    """Pick the option whose label starts with (or contains) the house number/name.

    options: list of (value, label). Prefers "<paon> <street>" over "<paon> <flat>",
    then any whole-word occurrence. Raises ValueError if nothing matches.
    """
    paon = str(paon).strip()
    p = re.escape(paon)
    for pattern in (rf"^{p}[\s,]+[A-Za-z]", rf"^{p}[\s,]", rf"(^|[\s,]){p}([\s,]|$)"):
        for value, label in options:
            if re.search(pattern, label.strip(), re.I):
                return value
    raise ValueError(f"No address matching '{paon}' found for this postcode")


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def find_uprn(self, postcode, paon):
        """Resolve a UPRN from postcode + house number via Lambeth's LLPG search."""
        res = requests.post(ADDRESS_SEARCH_URL, json={"postcode": postcode}, timeout=30)
        res.raise_for_status()
        results = (res.json().get("payload") or {}).get("results") or []
        if not results:
            raise ValueError(f"No addresses found for postcode {postcode}")
        # Whole properties first so "5" picks 5 Prescott Place, not a flat within it
        results.sort(key=lambda r: bool(r.get("SAO_TEXT") or r.get("SAO_START_NUMBER")))
        options = []
        for r in results:
            pao = f"{r.get('PAO_START_NUMBER', '')}{r.get('PAO_START_SUFFIX', '')}"
            label = " ".join(
                x for x in (pao, r.get("PAO_TEXT"), r.get("STREET"), r.get("SAO_TEXT")) if x
            )
            options.append((r["UPRN"], label))
        return match_address(options, paon)

    def parse_data(self, page: str, **kwargs) -> dict:

        """
        Parse bin collection data for a given UPRN from the Lambeth waste service API.
        
        Posts the UPRN to the Lambeth "GetServicesByUprn" endpoint, extracts services that include a next collection date and a container, normalizes commercial container types to either "recycling" (if the container name contains "Recycling") or "refuse", and returns a dictionary with a "bins" list where each entry contains the bin type and the collection date formatted according to `date_format`.
        
        Parameters:
            page (str): HTML or page content provided to the parser (not used by this implementation).
            uprn (str, optional, in kwargs): The UPRN to query.
            postcode, paon (str, optional, in kwargs): used to look up the UPRN when none is given.

        Returns:
            dict: A dictionary with a single key "bins" mapping to a list of objects with:
                - "type" (str): Bin type (e.g., "recycling", "refuse", or the container's DisplayPhrase).
                - "collectionDate" (str): Collection date formatted using `date_format`.
        
        Raises:
            ConnectionRefusedError: If the API response status code is not 200.
        """
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon") or kwargs.get("house_number")
        if not user_uprn and user_postcode and user_paon:
            user_uprn = self.find_uprn(user_postcode, user_paon)
        check_uprn(user_uprn)
        data = {"bins": []}

        url = "https://wasteservice.lambeth.gov.uk/WhitespaceComms/GetServicesByUprn"

        headers = CaseInsensitiveDict()
        headers["Content-Type"] = "application/json"

        body = {"uprn": user_uprn, "includeEventTypes": False, "includeFlags": True}
        json_data = json.dumps(body)

        res = requests.post(url, headers=headers, data=json_data, timeout=30)

        if res.status_code != 200:
            raise ConnectionRefusedError("Cannot connect to API!")

        json_data = res.json()

        if "SiteServices" in json_data:
            SiteServices = json_data["SiteServices"]
            for service in SiteServices:
                if "NextCollectionDate" in service:
                    NextCollectionDate = service["NextCollectionDate"]
                    if NextCollectionDate:
                        Container = service["Container"]
                        if Container:
                            if Container["DisplayPhrase"] == "commercial bin":
                                Bin_Type = (
                                    "recycling"
                                    if "Recycling" in Container["Name"]
                                    else "refuse"
                                )
                            else:
                                Bin_Type = Container["DisplayPhrase"]
                            dict_data = {
                                "type": Bin_Type,
                                "collectionDate": datetime.strptime(
                                    NextCollectionDate, "%d/%m/%Y"
                                ).strftime(date_format),
                            }
                            data["bins"].append(dict_data)

        return data