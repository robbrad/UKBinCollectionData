"""This script pulls (in one hit) the data from
Sheffield City Council Bins Data and outputs json"""

#!/usr/bin/env python3
import json
import re

# import the wonderful Beautiful Soup and the URL grabber
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

# Set a user agent so we look like a browser ;-)
USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
HEADERS = {"User-Agent": USER_AGENT}

# Make the Request - change the URL - find out your property number
req = Request("https://wasteservices.sheffield.gov.uk/property/XXXXXXXXXXX")
req.add_header("User-Agent", USER_AGENT)
fp = urlopen(req).read()

# decode the page
page = fp.decode("utf8")

# Make a BS4 object
soup = BeautifulSoup(page, features="html.parser")
soup.prettify()

# Form a JSON wrapper
data = {"bins": []}

# Search for the specific table using BS4
rows = soup.find("table", {"class": re.compile("table")}).find_all("tr")

# Loops the Rows
for row in rows:
    cells = row.find_all("td", {"class": lambda L: L and L.startswith("service-name")})

    if len(cells) > 0:
        collectionDatesRawData = row.find_all(
            "td", {"class": lambda L: L and L.startswith("next-service")}
        )[0].get_text(strip=True)
        collectionDate = collectionDatesRawData[16 : len(collectionDatesRawData)].split(
            ","
        )
        bin_type = row.find_all(
            "td", {"class": lambda L: L and L.startswith("service-name")}
        )[0].h4.get_text(strip=True)

        for collectDate in collectionDate:
            # Make each Bin element in the JSON
            dict_data = {
                "bin_type": bin_type,
                "collectionDate": collectDate,
            }

            # Add data to the main JSON Wrapper
            data["bins"].append(dict_data)

##Make the JSON
json_data = json.dumps(data, sort_keys=True, indent=4)

# Output the data - run this script with a redirect to send the output to a file
# Suggest Crontab
print(json_data)
