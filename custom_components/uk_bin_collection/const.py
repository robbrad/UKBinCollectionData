"""Constants for UK Bin Collection Data."""
from datetime import timedelta

from homeassistant.const import Platform

DEFAULT_NAME = "UK Bin Collection Data"

DOMAIN = "uk_bin_collection"

LOG_PREFIX = "[UKBinCollection] "

PLATFORMS = [Platform.SENSOR]

SCAN_INTERVAL = timedelta(hours=24)

STATE_ATTR_COLOUR = "colour"
STATE_ATTR_NEXT_COLLECTION = "next_collection"
STATE_ATTR_DAYS = "days"

DEVICE_CLASS = "bin_collection_schedule"

CONF_COUNCIL = "council"
CONF_URL = "url"
CONF_SKIP_URL = "skip_url"
CONF_UPRN = "uprn"
CONF_POSTCODE = "postcode"
CONF_HOUSE_NUMBER = "house_number"