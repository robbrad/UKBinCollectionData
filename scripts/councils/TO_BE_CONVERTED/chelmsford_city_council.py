#!/usr/bin/env python3

# This script pulls (in one hit) the data from Chelmsford Council Bins Data

# import the wonderful Beautiful Soup and the URL grabber
from urllib.request import Request, urlopen
import json
from bs4 import BeautifulSoup

# Set a user agent so we look like a browser ;-)
user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
headers = {"User-Agent": user_agent}

# Make the Request - change the URL
req = Request(
    "https://mychelmsford.secure.force.com/WasteServices/WM_WasteViewProperty?id=XXXXXXXXXXXXXXX"
)
req.add_header("User-Agent", user_agent)
fp = urlopen(req).read()

# decode the page
page = fp.decode("utf8")

# Make a BS4 object
soup = BeautifulSoup(page, features="html.parser")
soup.prettify()

# Form a JSON wrapper
data = {"bins": []}

# Search for the specific table using BS4
rows = soup.find(
    "tbody", {"id": lambda L: L and L.startswith("Registration:")}
).find_all("tr")

# Loops the Rows
for row in rows:

    # set the vars per bin and date for each row
    cells = row.find_all("td")
    binType = cells[1].get_text()
    lcDate = cells[2].get_text()
    ncDate = cells[3].get_text()
    fcDate = cells[4].get_text()

    # Make each Bin element in the JSON
    dict_data = {
        "BinType": binType,
        "Last Collection Date": lcDate,
        "Next Collection Date": ncDate,
        "Following Collection Date": fcDate,
    }

    # Add data to the main JSON Wrapper
    data["bins"].append(dict_data)

# Make the JSON
json_data = json.dumps(data, sort_keys=True, indent=4)

# Output the data - run this script with a redirect to send the output to a file
# Suggest Crontab
print(json_data)
