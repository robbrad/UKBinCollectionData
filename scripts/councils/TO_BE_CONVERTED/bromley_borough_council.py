#!/usr/bin/env python3
from urllib.request import Request, urlopen
import json
from bs4 import BeautifulSoup

user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
headers = {"User-Agent": user_agent}

# Replace URL
req = Request("https://recyclingservices.bromley.gov.uk/property/xxxxxxxxxx")
req.add_header("User-Agent", user_agent)

fp = urlopen(req).read()
page = fp.decode("utf8")

soup = BeautifulSoup(page, features="html.parser")
soup.prettify()

data = {}

for bins in soup.findAll("div", {"class": "service-wrapper"}):
    bin_type = bins.h3.text.strip()
    binCollection = bins.find("td", {"class": "next-service"})
    if (
        binCollection
    ):  # batteries don't have a service date or other info associated with them.
        data[bin_type] = binCollection.contents[-1].strip()

json_data = json.dumps(data)

print(json_data)
