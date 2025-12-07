import logging
import requests
from uk_bin_collection.uk_bin_collection.common import (
    check_postcode,
    check_uprn,
    date_format,
)
from datetime import datetime, timezone, timedelta
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
        """
        Initialize the CouncilClass instance.
        
        Calls the superclass initializer, creates a requests.Session assigned to self._session, and sets self._have_session to False to indicate that an authenticated session has not yet been established.
        """
        super().__init__()
        self._session = requests.Session()
        self._have_session = False

    def _initialise_session(self) -> None:
        """
        Establish an authenticated session with the remote service and mark the instance as having a valid session.
        
        Performs an HTTP GET to the configured session endpoint and verifies the JSON response contains an "auth-session" indicator. On success sets the instance flag that a session is available.
        
        Raises:
            requests.HTTPError: If the session request returned an HTTP error status.
            ValueError: If the response JSON cannot be decoded or does not contain an "auth-session" key.
        """
        response = self._session.get(SESSION_URL, timeout=60)
        response.raise_for_status()

        try:
            if not response.json().get("auth-session"):
                raise ValueError("Failed to obtain session cookie")
        except requests.exceptions.JSONDecodeError as e:
            raise ValueError("Failed to decode session response as JSON") from e

        self._have_session = True

    def _run_lookup(self, lookup_id: str, payload: dict) -> dict:
        """
        Run a lookup request and return the lookup's transformed rows data.
        
        Parameters:
            lookup_id (str): Lookup identifier appended as the `id` query parameter to the lookup endpoint.
            payload (dict): JSON body sent with the POST request.
        
        Returns:
            The `rows_data` value extracted from the response's `integration.transformed` object.
        
        Raises:
            ValueError: If the response is not valid JSON or does not contain the expected `integration.transformed.rows_data` structure.
        """
        if not self._have_session:
            self._initialise_session()

        response = self._session.post(
            f"{LOOKUP_URL}?id={lookup_id}", json=payload, timeout=60
        )
        response.raise_for_status()

        # Extract the nested data structure
        try:
            return response.json()["integration"]["transformed"]["rows_data"]
        except requests.exceptions.JSONDecodeError as e:
            raise ValueError("Failed to decode lookup response as JSON") from e
        except KeyError as e:
            logger.debug(f"Lookup response content: {response.text}")
            raise ValueError("Unexpected response structure from lookup") from e

    def _get_uprn_from_postcode_and_paon(self, postcode: str, paon: str) -> str:
        """
        Return the UPRN for the address at the given postcode matching the provided PAON.
        
        Parameters:
            postcode (str): Postcode to search.
            paon (str): Primary Addressable Object Name — house number or name to match.
        
        Returns:
            str: The matching UPRN.
        
        Raises:
            ValueError: If no addresses are found for the postcode or no address matches the PAON.
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
        """
        Obtain the bin collection schedule for a property identified by UPRN or by postcode and house number/name.
        
        Parameters:
            page (str): Unused but required by the interface.
            **kwargs: Identification parameters — provide either:
                uprn (str): The property's UPRN.
                OR
                postcode (str): The property's postcode.
                paon (str) or number (str): The property's primary addressable object name/number (required with postcode).
        
        Returns:
            dict: A dictionary with a "bins" key mapping to a list of collection entries, each containing `type` and `collectionDate`.
        
        Raises:
            ValueError: If required identification parameters are missing, input validation fails, or the remote lookup cannot resolve the property.
        """
        _ = page  # required by interface; response body is not used

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
            user_uprn = self._get_uprn_from_postcode_and_paon(user_postcode, user_paon)

        check_uprn(user_uprn)

        # (interestingly, we can retrieve arbitrary future dates by changing calcDate)
        payload = {
            "formValues": {
                "Section 1": {
                    "calcUPRN": {"value": user_uprn},
                    "calcDate": {
                        "value": datetime.now(timezone.utc).strftime("%d/%m/%Y")
                    },
                    "calcLang": {"value": "en"},
                }
            }
        }

        schedule = self._run_lookup(SCHEDULE_LOOKUP_ID, payload)
        return self._extract_bin_data(schedule)

    @staticmethod
    def _extract_bin_data(schedule: dict) -> dict:
        """
        Convert a schedule response into the standardized bins list.
        
        Parameters:
            schedule (dict): Mapping of schedule rows returned by the API where each value is a dict containing at least the keys "Service" and "Date".
        
        Returns:
            dict: {"bins": [ {"type": <service name>, "collectionDate": <date string formatted by date_format>} , ... ]}
        
        Raises:
            ValueError: If `schedule` is empty.
        
        Notes:
            - Rows missing required fields or containing unparsable dates are skipped and a warning is logged.
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

                # If the date (assuming current year) has already passed by more than 30 days, use next year
                if collection_date < now - timedelta(days=30):
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