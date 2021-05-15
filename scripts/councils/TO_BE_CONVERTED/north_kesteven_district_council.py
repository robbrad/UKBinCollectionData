#!/usr/bin/env python3
from urllib.request import Request, urlopen
import json
from bs4 import BeautifulSoup

user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
headers = {'User-Agent': user_agent}

#Replace URL
req = Request('https://www.n-kesteven.org.uk/bins/display?uprn=XXXXXXXXXX')
req.add_header('User-Agent', user_agent)

fp = urlopen(req).read()

page = fp.decode("utf8")

soup = BeautifulSoup(page, features="html.parser")
soup.prettify()

data = {}

for bins in soup.findAll("div", {"class" : lambda L: L and L.startswith('bg-')}):
    binType = bins.h3.text
    binCollection = bins.find_all("strong")[-1].text
    data[f'{binType}'] = f'{binCollection}'

json_data = json.dumps(data)

print(json_data)
