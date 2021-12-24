#!/usr/bin/env python3
from urllib.request import Request, urlopen
import json
from bs4 import BeautifulSoup

user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
headers = {"User-Agent": user_agent}

# Replace URL
req = Request("http://mydurham.durham.gov.uk/article/12690?uprn=XXXXXXXXXXXXXXXXXXX")
req.add_header("User-Agent", user_agent)

fp = urlopen(req).read()

page = fp.decode("utf8")

soup = BeautifulSoup(page, features="html.parser")
soup.prettify()

data = {}

for bins in soup.findAll(
    "div",
    {
        "id": lambda L: L
        and L.startswith("page_PageContentHolder_template_pnlArticleBody")
    },
):
    bin_type = bins.h2.text
    binDates = bins.find_all("p")
    binCollection = binDates[1].get_text(strip=True).split(": ", 1)[-1].split(".", 1)[0]
    data[bin_type] = binCollection

json_data = json.dumps(data)

print(json_data)
