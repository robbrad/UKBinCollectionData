# UK Bin Collection Data Utilities

This document provides an overview of the utility modules available in the UK Bin Collection Data project. These utilities are designed to make development easier and more robust.

## Table of Contents

- [Retry Mechanism](#retry-mechanism)
- [Caching](#caching)
- [HTTP Client](#http-client)
- [Validation](#validation)
- [Logging](#logging)

## Retry Mechanism

The retry mechanism provides a way to automatically retry functions that may fail due to transient errors, such as network issues or temporary server problems.

### Usage

```python
from uk_bin_collection.uk_bin_collection.utils.retry import retry

@retry(
    exceptions=(requests.RequestException, requests.Timeout),
    tries=3,
    delay=1.0,
    backoff=2.0
)
def fetch_data_from_council():
    # Your code here that might fail temporarily
    response = requests.get("https://council-website.gov.uk/bins")
    response.raise_for_status()
    return response.text
```

### Parameters

- `exceptions`: The exception(s) to catch and retry on. Default is `Exception`.
- `tries`: Number of times to try before giving up. Default is `3`.
- `delay`: Initial delay between retries in seconds. Default is `1.0`.
- `backoff`: Backoff multiplier. Default is `2.0`.
- `logger_func`: Logger function to use. Default is `None` (uses internal logger).

## Caching

The caching utility provides a way to cache function results to reduce API calls and improve performance.

### Usage

```python
from uk_bin_collection.uk_bin_collection.utils.cache import cached

@cached(ttl=3600)  # Cache for 1 hour
def get_bin_collection_data():
    # Your code here that's expensive to run
    return fetch_data_from_council()
```

### Cache Class

You can also use the `Cache` class directly for more control:

```python
from uk_bin_collection.uk_bin_collection.utils.cache import get_cache

cache = get_cache()

# Get a value from the cache
data = cache.get("my_key")

# Set a value in the cache
cache.set("my_key", data, ttl=3600)

# Invalidate a cache entry
cache.invalidate("my_key")
```

### Parameters

- `ttl`: Time to live in seconds. Default is `3600` (1 hour).
- `key_func`: Function to generate cache key from args and kwargs. Default is `None`.

## HTTP Client

The HTTP client provides a wrapper around the requests library with retry and caching capabilities.

### Usage

```python
from uk_bin_collection.uk_bin_collection.utils.http_client import get, post

# Simple GET request
response = get("https://council-website.gov.uk/bins")

# GET request with parameters
response = get(
    "https://council-website.gov.uk/bins",
    params={"postcode": "AB12 3CD"},
    headers={"User-Agent": "UKBinCollectionData/1.0"},
    timeout=30,
    cache=True
)

# POST request
response = post(
    "https://council-website.gov.uk/bins/search",
    data={"postcode": "AB12 3CD"},
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
```

### HttpClient Class

You can also create your own client instance for more control:

```python
from uk_bin_collection.uk_bin_collection.utils.http_client import HttpClient

client = HttpClient(
    timeout=60,
    max_retries=3,
    cache_ttl=3600,
    user_agent="MyCustomUserAgent/1.0"
)

response = client.get("https://council-website.gov.uk/bins")
```

## Validation

The validation utility provides functions to validate bin collection data and other common data types.

### Usage

```python
from uk_bin_collection.uk_bin_collection.utils.validation import (
    validate_bin_collection_data,
    validate_postcode,
    validate_uprn,
    ValidationError
)

# Validate bin collection data
try:
    validate_bin_collection_data(data)
    print("Data is valid")
except ValidationError as e:
    print(f"Data validation error: {e}")

# Validate a postcode
if validate_postcode("AB12 3CD"):
    print("Postcode is valid")
else:
    print("Postcode is invalid")

# Validate a UPRN
if validate_uprn("123456789012"):
    print("UPRN is valid")
else:
    print("UPRN is invalid")
```

### Bin Type Normalization

You can normalize bin types for consistency:

```python
from uk_bin_collection.uk_bin_collection.utils.validation import normalize_bin_type

normalized = normalize_bin_type("Black Bin (General Waste)")
# Returns "general"
```

## Logging

The logging utility provides a unified logging system for the project.

### Usage

```python
from uk_bin_collection.uk_bin_collection.utils.logger import get_logger, setup_logging

# Set up logging (only needed once, usually in the main script)
setup_logging(
    log_level="INFO",
    log_file="/path/to/log/file.log",
    log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get a logger for your module
logger = get_logger(__name__)

# Log messages
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")
```

### Parameters for setup_logging

- `log_level`: Logging level. Default is `logging.INFO`.
- `log_file`: Path to log file. Default is `None` (logs to console only).
- `log_format`: Log message format. Default is `%(asctime)s - %(name)s - %(levelname)s - %(message)s`.
- `max_file_size`: Maximum size of log file before rotation in bytes. Default is `10 * 1024 * 1024` (10 MB).
- `backup_count`: Number of backup log files to keep. Default is `3`.