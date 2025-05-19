# Takes a latitude and longitude and returns property information

import aiohttp
import base64
import logging

_LOGGER = logging.getLogger(__name__) 

key_b64 = "QUl6YVN5RGtDb2Q2ODZOR3N5Ulk3UXZtNk5CMDlRT3VTSFAzT2xV" # 2025-05-17
API_KEY = base64.b64decode(key_b64).decode("utf-8")

async def async_get_property_info(lat, lng):
    """
    Async version of get_property_info that uses aiohttp instead of requests.
    Given latitude and longitude, returns a dict with property information or None if an error occurs.
    
    Returns:
    - LAD24CD code (string) from postcodes.io
    - Postcode (string) from Google Geocode
    - Street Name (string) from Google Geocode
    """
    try:
        # 1. Get address info from Google Geocode API
        google_url = (
            f"https://maps.googleapis.com/maps/api/geocode/json"
            f"?latlng={lat},{lng}&result_type=street_address&key={API_KEY}"
        )
        
        async with aiohttp.ClientSession() as session:
            async with session.get(google_url, timeout=10) as google_resp:
                if google_resp.status != 200:
                    _LOGGER.warning(f"Google Geocode API returned status {google_resp.status}")
                    return None
                    
                google_data = await google_resp.json()
                
        # Check for API key related errors
        if google_data.get("status") in ["REQUEST_DENIED", "INVALID_REQUEST", "OVER_QUERY_LIMIT"]:
            error_message = google_data.get("error_message", "Unknown API error")
            _LOGGER.error(f"Google Geocode API error: {google_data['status']} - {error_message}")
            return None
                
        if not google_data.get("results"):
            _LOGGER.warning("No results from Google Geocode API")
            return None
            
        address_components = google_data["results"][0]["address_components"]

        # Extract postcode and street name
        postcode = None
        street_name = None
        postal_town = None
        for comp in address_components:
            if "postal_code" in comp["types"]:
                postcode = comp["long_name"].replace(" ", "").lower()  # for postcodes.io
                postcode_for_output = comp["long_name"]  # for output
            if "route" in comp["types"]:
                street_name = comp["long_name"]
            if "postal_town" in comp["types"]:
                postal_town = comp["long_name"]
                
        if not postcode or not street_name:
            _LOGGER.warning("Could not find postcode or street name in Google response")
            return None

        # 2. Get LAD24CD code from postcodes.io
        postcodes_url = f"https://api.postcodes.io/postcodes/{postcode}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(postcodes_url, timeout=10) as postcodes_resp:
                if postcodes_resp.status != 200:
                    _LOGGER.warning(f"postcodes.io API returned status {postcodes_resp.status}")
                    return None
                    
                postcodes_data = await postcodes_resp.json()
                
        if postcodes_data["status"] != 200 or not postcodes_data.get("result"):
            _LOGGER.warning("No results from postcodes.io")
            return None
            
        lad24cd = postcodes_data["result"]["codes"].get("admin_district")
        if not lad24cd:
            _LOGGER.warning("No admin_district code found in postcodes.io response")
            return None
            
        admin_ward = postcodes_data["result"].get("admin_ward", "")

        _LOGGER.debug(
            "Retrieved property info - Street: %s, Ward: %s, Postcode: %s, LAD24CD: %s, Town: %s",
            street_name, admin_ward, postcode_for_output, lad24cd, postal_town or ""
        )

        return {
            "street_name": street_name,
            "admin_ward": admin_ward,
            "postcode": postcode_for_output,
            "LAD24CD": lad24cd,
            "postal_town": postal_town or ""  # Return empty string if postal_town not found
        }
        
    except aiohttp.ClientError as e:
        _LOGGER.warning(f"HTTP request error: {e}")
        return None
    except aiohttp.ServerTimeoutError:
        _LOGGER.warning("Request timed out")
        return None
    except KeyError as e:
        _LOGGER.warning(f"Expected key not found in API response: {e}")
        return None
    except Exception as e:
        _LOGGER.error(f"Unexpected error fetching property info: {e}")
        return None