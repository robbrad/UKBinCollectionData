# Example Council Implementation

This document shows how to implement a council class using the new utilities.

## Basic Structure

```python
from uk_bin_collection.uk_bin_collection.utils.retry import retry
from uk_bin_collection.uk_bin_collection.utils.cache import cached
from uk_bin_collection.uk_bin_collection.utils.http_client import get as http_get
from uk_bin_collection.uk_bin_collection.utils.logger import get_logger

# Get a logger for this module
logger = get_logger(__name__)

class ExampleCouncil:
    """Example council implementation using the new utilities."""
    
    # Required class variables
    postcode_required = True
    paon_required = True
    
    def __init__(self, url):
        self.url = url
        self.postcode = None
        self.paon = None
    
    @cached(ttl=3600)  # Cache for 1 hour
    @retry(tries=3, delay=1, backoff=2)
    def get_data(self):
        """Get bin collection data for this council."""
        logger.info(f"Fetching data for postcode {self.postcode}")
        
        # Construct the URL with parameters
        params = {
            "postcode": self.postcode,
            "house_number": self.paon
        }
        
        # Make the request with automatic retry
        response = http_get(self.url, params=params)
        
        # Process the response
        # ...
        
        # Return the data in the standard format
        return [
            {
                "type": "General Waste",
                "date": "01/01/2023"
            },
            {
                "type": "Recycling",
                "date": "08/01/2023"
            }
        ]
```

## Complete Example

For a complete example, see the updated council class template:
`/workspaces/UKBinCollectionData/uk_bin_collection/uk_bin_collection/councils/council_class_template/councilclasstemplate.py`