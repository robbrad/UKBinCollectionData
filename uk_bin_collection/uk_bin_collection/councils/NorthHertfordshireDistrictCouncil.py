# Uses Cloud9 mobile API to fetch waste collection data
# API endpoint: https://apps.cloud9technologies.com/northherts/citizenmobile/mobileapi/wastecollections/{uprn}

import json
from datetime import datetime

import requests

from uk_bin_collection.uk_bin_collection.common import (
    check_paon,
    check_postcode,
    check_uprn,
    date_format
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# Mobile API constants
MOBILE_API_BASE = "https://apps.cloud9technologies.com/northherts/citizenmobile/mobileapi"
# This auth header is extracted from the hardcoded value present in the mobile app
# https://play.google.com/store/apps/details?id=com.cloud9technologies.northhertsd
MOBILE_API_AUTH = "Basic Y2xvdWQ5OmlkQmNWNGJvcjU="
MOBILE_API_HEADERS = {
    "Accept": "application/json",
    "Authorization": MOBILE_API_AUTH,
    "X-Api-Version": "2",
    "X-App-Version": "3.0.56",
    "X-Platform": "android",
    "User-Agent": "okhttp/4.9.2",
}
MOBILE_API_NUM_CONTAINERS = 8


def lookup_uprn(postcode: str, paon: str) -> str:
    """
    Lookup UPRN from postcode and house number using the Cloud9 addresses API.

    Args:
        postcode: The postcode to search for
        paon: The house number/name (Primary Addressable Object Name)

    Returns:
        str: The UPRN for the address

    Raises:
        ValueError: If no matching address is found or if the API request fails
    """

    if not postcode:
        raise ValueError("Postcode is required")

    if not paon:
        raise ValueError("House number/name (paon) is required")

    postcode = postcode.strip()
    paon = paon.strip().lower()

    url = f"{MOBILE_API_BASE}/addresses"

    try:
        response = requests.get(url, headers=MOBILE_API_HEADERS, timeout=30, params={"postcode": postcode})
    except requests.RequestException as exc:
        raise ValueError("Addresses API request failed") from exc

    if response.status_code != 200:
        raise ValueError(
            f"Addresses API returned status {response.status_code}. "
            f"Please check your postcode is correct."
        )

    try:
        api_response = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        raise ValueError("Addresses API returned invalid JSON") from exc
    addresses = api_response.get("addresses", [])

    if not addresses:
        raise ValueError(
            f"No addresses found for postcode '{postcode}'. "
            f"Please check your postcode is correct."
        )

    # Search for matching address by paon (house number/name)
    # The paon could appear in addressLine1 or addressLine2
    matching_addresses = []
    for address in addresses:
        address_line1 = address.get("addressLine1", "").lower()
        address_line2 = address.get("addressLine2", "").lower()

        # Check if paon matches the start of addressLine1 or addressLine2
        first_parts = []
        for line in (address_line1, address_line2):
            if line.strip():
                split_line = line.split()
                if split_line:
                    first_parts.append(split_line[0])
        if paon in first_parts:
            matching_addresses.append(address)

    if not matching_addresses:
        raise ValueError(
            f"No address found matching house number/name '{paon}' for postcode '{postcode}'. "
            f"Found {len(addresses)} addresses for this postcode, but none matched. "
            f"You can find your UPRN at: https://www.findmyaddress.co.uk/search?postcode={postcode}"
        )

    if len(matching_addresses) > 1:
        # Multiple matches - Raise a ValueError so the user can remediate
        raise ValueError(
            f"Multiple addresses found matching '{paon}' for postcode '{postcode}'. "
            f"Please provide the UPRN directly for more accurate results. "
            f"You can find your UPRN at: https://www.findmyaddress.co.uk/search?postcode={postcode}"
        )

    return matching_addresses[0]["uprn"]


def fetch_mobile_api(uprn: str) -> dict:
    """
    Calls the Cloud9 mobile API to get waste collection data.

    Args:
        uprn: The Unique Property Reference Number

    Returns:
        dict: JSON response from the mobile API

    Raises:
        ValueError: If the API request fails, the response status is not 200, or the response contains invalid JSON.
    """
    url = f"{MOBILE_API_BASE}/wastecollections/{uprn}"

    # Perform the HTTP request and surface network-layer errors clearly
    try:
        response = requests.get(url, headers=MOBILE_API_HEADERS, timeout=30)
    except requests.RequestException as exc:
        raise ValueError("Mobile API request failed") from exc

    if response.status_code != 200:
        raise ValueError(
            f"Mobile API returned status {response.status_code}. "
            f"Please check your UPRN is correct."
        )

    # Decode JSON and surface parsing errors clearly
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as exc:
        raise ValueError("Mobile API returned invalid JSON") from exc


class CouncilClass(AbstractGetBinDataClass):
    """
    Council class for North Hertfordshire District Council.
    Uses the Cloud9 mobile API to fetch bin collection data.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        """
        Parse bin collection data using the Cloud9 mobile API.

        Args:
            page: Unused (kept for interface compatibility)
            **kwargs: Must contain either 'uprn' or both 'postcode' and 'paon'

        Returns:
            dict: Bin collection data in standard format
        """
        data = {"bins": []}

        # Get UPRN either directly or via lookup

        uprn = kwargs.get("uprn")

        if uprn:
            check_uprn(uprn)
        else:
            # Try to lookup UPRN from postcode and house number
            # This is provided to maintain backward compatibility with the existing postcode/paon input method
            postcode = kwargs.get("postcode")
            paon = kwargs.get("paon")
            check_postcode(postcode)
            check_paon(paon)

            # Attempt UPRN lookup using postcode and paon
            uprn = lookup_uprn(postcode=postcode, paon=paon)


        # Fetch data from mobile API
        api_response = fetch_mobile_api(uprn)

        # Parse the API response - Cloud9 API returns WasteCollectionDates with 8 containers
        # Response structure: {"wasteCollectionDates": {"container1CollectionDetails": {...}, ...}}
        waste_collection_dates = api_response.get("wasteCollectionDates", {})

        if not waste_collection_dates:
            raise ValueError(
                f"No wasteCollectionDates found in API response. API response: {json.dumps(api_response)[:200]}"
            )

        # Process all 8 possible containers
        for container_num in range(1, MOBILE_API_NUM_CONTAINERS + 1):
            container_key = f"container{container_num}CollectionDetails"
            container = waste_collection_dates.get(container_key)

            if not container or not isinstance(container, dict):
                continue

            # Extract collection date
            collection_date_str = container.get("collectionDate", "")

            # Skip empty collection dates
            if not collection_date_str:
                continue

            # Extract container description (bin type)
            bin_type = container.get("containerDescription", f"Container {container_num}")
            try:
                collection_datetime = datetime.fromisoformat(collection_date_str)
            except ValueError:
                # skip bins with invalid date format and continue processing
                continue

            # Parse the date - API returns ISO format like "2025-11-25T00:00:00"
            bin_entry = {
                "type": bin_type,
                "collectionDate": collection_datetime.strftime(date_format),
                "_sort_date": collection_datetime
            }

            data["bins"].append(bin_entry)

        if not data["bins"]:
            raise ValueError(
                "No valid bin collection data could be extracted from the API response"
            )

        # Sort the bin collections by date
        data["bins"].sort(
            key=lambda x: x.pop("_sort_date")
        )

        return data

