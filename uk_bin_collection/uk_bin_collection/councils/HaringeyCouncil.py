import requests

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
        user_uprn = kwargs.get("uprn")
        check_postcode(user_postcode)
        bindata = {"bins": []}

        COUNCIL_ID = "45"
        SEARCH_URL = "https://wastecollections.haringey.gov.uk/api/getPropertySearch"
        DAYS_URL = "https://wastecollections.haringey.gov.uk/api/getCollectionDays"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

        s = requests.session()
        r = s.post(
            SEARCH_URL,
            json={"councilId": COUNCIL_ID, "searchQuery": user_postcode},
            headers=headers,
        )
        r.raise_for_status()
        results = r.json().get("data", [])
        if not results:
            raise ValueError("No addresses found for this postcode")

        if user_uprn:
            check_uprn(user_uprn)
            match = next((a for a in results if a.get("uprn") == user_uprn), None)
            if not match:
                raise ValueError(
                    f"Could not match UPRN '{user_uprn}' in address results"
                )
        elif user_paon:
            check_paon(user_paon)
            paon_norm = str(user_paon).strip().upper()
            match = next(
                (a for a in results if a["name"].upper().startswith(paon_norm + " ")),
                None,
            )
            if not match:
                raise ValueError(
                    f"Could not match house number '{user_paon}' in address results"
                )
        elif len(results) == 1:
            match = results[0]
        else:
            raise ValueError(
                "Multiple addresses found for this postcode; provide a UPRN or house number to disambiguate"
            )

        r = s.post(
            DAYS_URL,
            json={
                "pointId": match["id"],
                "pointType": "PointAddress",
                "councilId": COUNCIL_ID,
            },
            headers=headers,
        )
        r.raise_for_status()
        services = r.json().get("activeServices", [])

        today = datetime.now().date()
        for service in services:
            bin_type = service.get("taskTypeName")
            for schedule in service.get("serviceSchedules", []):
                # Each service returns its last completed collection alongside
                # the next one - skip completed entries and anything in the past.
                if schedule.get("coreStateName") == "Complete":
                    continue
                date_str = schedule.get("currentScheduledDate")
                if not date_str:
                    continue
                collection_date = datetime.fromisoformat(date_str).date()
                if collection_date < today:
                    continue
                bindata["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
