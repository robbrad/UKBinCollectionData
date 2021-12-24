#!/usr/bin/env python3
from urllib.request import Request, urlopen
import json
import re
from bs4 import BeautifulSoup

user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
headers = {"User-Agent": user_agent}

# Replace URL
req = Request("https://myaccount.stockport.gov.uk/bin-collections/show/xxxxxxxxxxxx")
req.add_header("User-Agent", user_agent)

fp = urlopen(req).read()
page = fp.decode("utf8")

soup = BeautifulSoup(page, features="html.parser")
soup.prettify()

data = {}

for bins in soup.select('div[class*="service-item"]'):
    bin_type = bins.div.h3.text.strip()
    binCollection = bins.select("div > p")[1].get_text(strip=True)
    # binImage = "https://myaccount.stockport.gov.uk" + bins.img['src']
    if (
        binCollection
    ):  # batteries don't have a service date or other info associated with them.
        data[bin_type] = binCollection

json_data = json.dumps(data)

print(json_data)
