DOMAIN = "uk_bin_collection"

async def async_setup(hass, config):
    """Set up the UK Bin Collection component."""
    hass.data.setdefault(DOMAIN, {})
    return True
