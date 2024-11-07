"""Constants for UK Bin Collection Data."""

from datetime import timedelta

from homeassistant.const import Platform

DEFAULT_NAME = "UK Bin Collection Data"

DOMAIN = "uk_bin_collection"

LOG_PREFIX = "[UKBinCollection] "

PLATFORMS = [Platform.SENSOR]

STATE_ATTR_COLOUR = "colour"
STATE_ATTR_NEXT_COLLECTION = "next_collection"
STATE_ATTR_DAYS = "days"

DEVICE_CLASS = "bin_collection_schedule"

PLATFORMS = ["sensor", "calendar"]

SELENIUM_SERVER_URLS = ["http://localhost:4444", "http://selenium:4444"]

BROWSER_BINARIES = ["chromium", "chromium-browser", "google-chrome"]