import logging
import requests
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

logger = logging.getLogger(__name__)

BASE_URL = "https://myaccount.anglesey.gov.wales"
SESSION_URL = f"{BASE_URL}/authapi/isauthenticated?uri=https%3A%2F%2Fmyaccount.anglesey.gov.wales&hostname=myaccount.anglesey.gov.wales&withCredentials=true"
LOOKUP_URL = f"{BASE_URL}/apibroker/runLookup"

# Lookup IDs for different API endpoints
ADDRESS_LOOKUP_ID = "61c43f6dabddb"  # Get addresses by postcode
SCHEDULE_LOOKUP_ID = "6362261cd6bd9"  # Get bin schedule by UPRN


class CouncilClass(AbstractGetBinDataClass):
    """
    Isle of Anglesey Council bin collection scraper.
    """

    def __init__(self):
        super().__init__()
        self._session = requests.Session()
        self._have_session = False

    def _initialise_session(self) -> None:
        """Initialize session by obtaining authentication cookie."""
        response = self._session.get(SESSION_URL)
        response.raise_for_status()

        if not response.json().get("auth-session"):
            raise ValueError("Failed to obtain session cookie")

        self._have_session = True

    def _run_lookup(self, lookup_id: str, payload: dict) -> dict:
        """Execute API lookup with given ID and payload.

        Args:
            lookup_id: The ID of the lookup to run
            payload: The JSON payload to send

        Returns:
            The transformed rows data from the response
        """
        if not self._have_session:
            self._initialise_session()

        response = self._session.post(f"{LOOKUP_URL}?id={lookup_id}", json=payload)
        response.raise_for_status()

        # Extract the nested data structure
        return (
            response.json()
            .get("integration", {})
            .get("transformed", {})
            .get("rows_data", {})
        )

    def _get_uprn_from_postcode(self, postcode: str, paon: str) -> str:
        """Look up UPRN from postcode and house number/name.

        Args:
            postcode: The postcode to search
            paon: Property number or name (Primary Addressable Object Name)

        Returns:
            The UPRN for the matched address

        Raises:
            ValueError: If no addresses found or no match for the PAON
        """
        payload = {
            "formValues": {"Section 1": {"postcode_search": {"value": postcode}}}
        }

        addresses = self._run_lookup(ADDRESS_LOOKUP_ID, payload)

        if not addresses:
            raise ValueError(f"No addresses found for postcode {postcode}")

        paon_normalized = paon.strip().lower()

        # Search for matching address
        for uprn, address_data in addresses.items():
            if any(
                paon_normalized in field.lower()
                for field in [
                    address_data.get("display", ""),
                    address_data.get("house", ""),
                    address_data.get("flatHouse", ""),
                ]
            ):
                return uprn

        # No match found - provide helpful error
        available = [addr.get("display", "") for addr in addresses.values()]
        raise ValueError(
            f"Could not find address matching '{paon}' in postcode {postcode}. "
            f"Available addresses: {', '.join(available[:5])}"
            f"{'...' if len(available) > 5 else ''}"
        )

    def parse_data(self, page: str, **kwargs) -> dict:
        """Parse bin collection data from council API.

        Args:
            page: Unused (required by interface)
            **kwargs: Either 'uprn' or ('postcode' and 'paon'/'number')

        Returns:
            Dictionary containing bin collection schedule
        """

        user_uprn = kwargs.get("uprn")

        if not user_uprn:
            # Look up UPRN from postcode + address
            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon") or kwargs.get("number")

            if not user_postcode:
                raise ValueError("Either 'uprn' or 'postcode' is required")
            if not user_paon:
                raise ValueError(
                    "House number or name ('paon' or 'number') is required with postcode"
                )

            check_postcode(user_postcode)
            user_uprn = self._get_uprn_from_postcode(user_postcode, user_paon)

        check_uprn(user_uprn)

        # (interestingly, we can retrieve arbitrary future dates by changing calcDate)
        payload = {
            "formValues": {
                "Section 1": {
                    "calcUPRN": {"value": user_uprn},
                    "calcDate": {"value": datetime.now().strftime("%d/%m/%Y")},
                    "calcLang": {"value": "en"},
                }
            }
        }

        schedule = self._run_lookup(SCHEDULE_LOOKUP_ID, payload)
        return self._extract_bin_data(schedule)

    @staticmethod
    def _extract_bin_data(schedule: dict) -> dict:
        """Extract bin collection data from API response.

        Args:
            schedule: The schedule data from the API

        Returns:
            Dictionary with 'bins' list containing collection dates
        """
        if not schedule:
            raise ValueError("No collection data found")

        bins = []
        now = datetime.now()
        current_year = now.year

        for row in schedule.values():
            try:
                service = row["Service"]
                date_str = row["Date"]

                # Parse date without year, then add current year
                collection_date = datetime.strptime(
                    f"{date_str} {current_year}", "%d %B %Y"
                )

                # If date has passed, use next year instead
                if collection_date < now:
                    collection_date = collection_date.replace(year=current_year + 1)

                bins.append(
                    {
                        "type": service,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping invalid row: {e}", exc_info=True)

        return {"bins": bins}
