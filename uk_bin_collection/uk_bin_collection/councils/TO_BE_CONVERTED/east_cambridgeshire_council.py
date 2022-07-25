#!/usr/bin/env python3
from urllib.request import Request, urlopen
from datetime import datetime, date
import json
from bs4 import BeautifulSoup

user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
headers = {"User-Agent": user_agent}

# Replace UPRN
uprn = "xxxxxxxxxxxx"
url = (
    "https://eastcambs-self.achieveservice.com/appshost/firmstep/self/apps/custompage/bincollections?language=en&uprn="
    + uprn
)
req = Request(url)
req.add_header("User-Agent", user_agent)

fp = urlopen(req).read()

page = fp.decode("utf8")

soup = BeautifulSoup(page, features="html.parser")
soup.prettify()

# Form a JSON wrapper
data = {"bins": []}

for bins in soup.findAll("div", {"class": "row collectionsrow"}):

    # Find the collection dates
    _, bin_type, date = bins.find_all("div")
    bin_type = bin_type.text
    date = datetime.strptime(date.text, "%a - %d %b %Y").date()

    data["bins"].append({"BinType": bin_type, "collectionDate": date.isoformat()})


json_data = json.dumps(data, sort_keys=True, indent=4)

print(json_data)
