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
