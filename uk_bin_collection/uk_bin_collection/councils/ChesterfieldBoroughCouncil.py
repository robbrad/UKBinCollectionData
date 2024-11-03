import json
import logging
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import check_uprn, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
import urllib3


# Suppress only the single warning from urllib3 needed.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_LOGGER = logging.getLogger(__name__)

class CouncilClass(AbstractGetBinDataClass):
    """
    Implementation for Chesterfield Borough Council waste collection data retrieval.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        """
        Fetch and parse waste collection data for Chesterfield Borough Council.

        Args:
            page (str): Not used in this implementation.
            **kwargs: Should contain 'uprn' key.

        Returns:
            dict: Parsed bin collection data.
        """
        # Get and check UPRN
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        # Define API URLs
        API_URLS = {
            "session": "https://www.chesterfield.gov.uk/bins-and-recycling/bin-collections/check-bin-collections.aspx",
            "fwuid": "https://myaccount.chesterfield.gov.uk/anonymous/c/cbc_VE_CollectionDaysLO.app?aura.format=JSON&aura.formatAdapter=LIGHTNING_OUT",
            "search": "https://myaccount.chesterfield.gov.uk/anonymous/aura?r=2&aura.ApexAction.execute=1",
        }

        HEADERS = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Initialize session
        session = requests.Session()

        try:
            # Step 1: Get session
            session.get(API_URLS["session"], headers=HEADERS, verify=False)

            # Step 2: Get fwuid
            fwuid_response = session.get(API_URLS["fwuid"], headers=HEADERS, verify=False)
            fwuid_data = fwuid_response.json()
            fwuid = fwuid_data.get("auraConfig", {}).get("context", {}).get("fwuid")

            if not fwuid:
                _LOGGER.error("Failed to retrieve fwuid from the response.")
                return bindata

            # Step 3: Prepare payload for UPRN search
            payload = {
                "message": json.dumps({
                    "actions": [{
                        "id": "4;a",
                        "descriptor": "aura://ApexActionController/ACTION$execute",
                        "callingDescriptor": "UNKNOWN",
                        "params": {
                            "namespace": "",
                            "classname": "CBC_VE_CollectionDays",
                            "method": "getServicesByUPRN",
                            "params": {
                                "propertyUprn": user_uprn,
                                "executedFrom": "Main Website"
                            },
                            "cacheable": False,
                            "isContinuation": False
                        }
                    }]
                }),
                "aura.context": json.dumps({
                    "mode": "PROD",
                    "fwuid": fwuid,
                    "app": "c:cbc_VE_CollectionDaysLO",
                    "loaded": {
                        "APPLICATION@markup://c:cbc_VE_CollectionDaysLO": "pqeNg7kPWCbx1pO8sIjdLA"
                    },
                    "dn": [],
                    "globals": {},
                    "uad": True
                }),
                "aura.pageURI": "/bins-and-recycling/bin-collections/check-bin-collections.aspx",
                "aura.token": "null",
            }

            # Step 4: Make POST request to fetch collection data
            search_response = session.post(
                API_URLS["search"],
                data=payload,
                headers=HEADERS,
                verify=False
            )
            search_data = search_response.json()

            # Step 5: Extract service units
            service_units = search_data.get("actions", [])[0].get("returnValue", {}).get("returnValue", {}).get("serviceUnits", [])

            if not service_units:
                _LOGGER.warning("No service units found for the given UPRN.")
                return bindata

            # Initialize dictionary to store bin dates
            bin_schedule = {}

            # Define icon mapping
            ICON_MAP = {
                "DOMESTIC REFUSE": "mdi:trash-can",
                "DOMESTIC RECYCLING": "mdi:recycle",
                "DOMESTIC ORGANIC": "mdi:leaf",
            }

            # Define regex pattern to capture day and date (e.g., Tue 5 Nov)
            date_pattern = re.compile(r"\b\w{3} \d{1,2} \w{3}\b")

            current_year = datetime.now().year

            # Process each service unit
            for item in service_units:
                try:
                    waste_type = item["serviceTasks"][0]["taskTypeName"]
                    waste_type = str(waste_type).replace("Collect ", "").upper()
                except (IndexError, KeyError):
                    _LOGGER.debug("Skipping a service unit due to missing data.")
                    continue

                # Extract the next scheduled date
                try:
                    dt_zulu = item["serviceTasks"][0]["serviceTaskSchedules"][0]["nextInstance"]["currentScheduledDate"]
                    dt_utc = datetime.strptime(dt_zulu, "%Y-%m-%dT%H:%M:%S.%f%z")
                    dt_local = dt_utc.astimezone(None)
                    collection_date = dt_local.date()
                except (IndexError, KeyError, ValueError) as e:
                    _LOGGER.warning(f"Failed to parse date for {waste_type}: {e}")
                    continue

                # Append to bin_schedule
                bin_schedule[waste_type] = collection_date.strftime(date_format)

            # Convert bin_schedule to the expected format
            for bin_type, collection_date in bin_schedule.items():
                dict_data = {
                    "type": bin_type,
                    "collectionDate": collection_date,
                }
                bindata["bins"].append(dict_data)

            # Sort the bins by collection date
            bindata["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
            )

        except requests.RequestException as e:
            _LOGGER.error(f"Network error occurred: {e}")
        except json.JSONDecodeError as e:
            _LOGGER.error(f"JSON decoding failed: {e}")
        except Exception as e:
            _LOGGER.error(f"An unexpected error occurred: {e}")

        return bindata
