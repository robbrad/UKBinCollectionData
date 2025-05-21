"""
# Data Structures Reference

URL Constants:
    COUNCIL_DATA_URL: str
        The URL used to fetch the list of councils from the main repository.

    SELENIUM_SERVER_URLS: List[str]
        A list of URLs for Selenium server instances to be checked for availability.

Data Storage (self.data):
    "council_list": Dict[str, Dict[str, Any]]
        Stores all the councils with their metadata.
        Example:
        {
            "AberdeenshireCouncil": {
                "LAD24CD": "S12000034",
                "uprn": "151176430",
                "url": "https://online.aberdeenshire.gov.uk",
                "wiki_command_url_override": "https://online.aberdeenshire.gov.uk",
                "wiki_name": "Aberdeenshire",
                "wiki_note": "You will need to use [FindMyAddress](https://www.findmyaddress.co.uk/search) to find the UPRN."
            },
        }

    "property_info": Dict[str, str]
        Stores property information fetched from Google Maps and Postcodes.io.
        Example:
        {
            "street_name": "High Street",
            "admin_ward": "Brighton Central",
            "postcode": "BN1 1AA",
            "LAD24CD": "E07000223",
            "postal_town": "Brighton"
        }

    "detected_council": Optional[str]
        The auto-detected council from LAD24CD.

    "detected_postcode": Optional[str]
        The auto-detected postcode from Google Maps.

    "selenium_status": Dict[str, bool]
        Maps Selenium server URLs to their availability.
        Example:
        {
            "http://localhost:4444/": True,
            "http://selenium-server:4444/": False
        }

    "selected_council": Optional[str]
        The council selected by the user during the configuration flow.

Schemas:
    user_schema: voluptuous.Schema
        Schema for user selection of council.

    council_schema: voluptuous.Schema
        Schema for configuring council-specific information.

    selenium_schema: voluptuous.Schema
        Schema for configuring Selenium options.

    advanced_schema: voluptuous.Schema
        Schema for configuring advanced settings like refresh intervals and timeouts.
"""

import asyncio
from .utils import get_councils_json, check_selenium_server, check_chromium_installed
from .property_info import async_get_property_info
from .const import COUNCIL_DATA_URL, SELENIUM_SERVER_URLS  # Import SELENIUM_SERVER_URLS
import logging

_LOGGER = logging.getLogger(__name__)

async def initialisation_data(self):
    """Initialise council data, property info, and selenium status."""
    
    # Fetch all councils and cache in self.data
    try:
        self.data["council_list"] = await get_councils_json(COUNCIL_DATA_URL)
    except ValueError as e:
        _LOGGER.error(f"Failed to fetch council data: {e}")
        return self.async_abort(reason="council_data_unavailable")
    
    # Fetch property info using Home Assistant's configured coordinates
    self.data["property_info"] = {}  # Initialize as empty dict
    
    # Get coordinates from Home Assistant configuration
    if hasattr(self, 'hass') and self.hass is not None:
        try:
            latitude = self.hass.config.latitude
            longitude = self.hass.config.longitude
            
            if latitude == 0 and longitude == 0:
                _LOGGER.warning("Home location not set in Home Assistant configuration")
            else:
                _LOGGER.debug("Fetching property info for coordinates: (%s, %s)", latitude, longitude)
                property_info = await async_get_property_info(latitude, longitude)
                
                # Only proceed if we got valid property info
                if property_info:
                    self.data["property_info"] = property_info
                    
                    # Attempt to auto-detect the council based on LAD24CD
                    lad_code = property_info.get("LAD24CD")
                    if lad_code:
                        for council_key, council_data in self.data["council_list"].items():
                            if council_data.get("LAD24CD") == lad_code:
                                self.data["detected_council"] = council_key
                                self.data["detected_postcode"] = property_info.get("postcode")
                                _LOGGER.info(f"Detected council: {council_data['wiki_name']} for LAD24CD: {lad_code}")
                                break
                        else:
                            _LOGGER.info(f"No matching council found for LAD24CD: {lad_code}")
                else:
                    _LOGGER.warning("Could not retrieve property information from coordinates")
        except Exception as e:
            _LOGGER.error(f"Error during property info processing: {e}")
    else:
        _LOGGER.warning("Home Assistant instance not available, cannot fetch property info")

    # Pre-check Selenium Servers
    self.data["selenium_status"] = {}  # Initialize as empty dict
    try:
        _LOGGER.debug(f"Checking Selenium servers: {SELENIUM_SERVER_URLS}")
        
        for url in SELENIUM_SERVER_URLS:
            is_available = await check_selenium_server(url)
            self.data["selenium_status"][url] = is_available
            _LOGGER.debug(f"Selenium server {url} is {'available' if is_available else 'unavailable'}")
            
    except Exception as e:
        _LOGGER.error(f"Error checking Selenium servers: {e}")