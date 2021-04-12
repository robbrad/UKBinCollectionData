#!/usr/bin/env python3
from urllib.request import Request, urlopen
import json
from bs4 import BeautifulSoup

user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
headers = {'User-Agent': user_agent}

#Replace XXXXXX
req = Request('https://estates7.warwickdc.gov.uk/PropertyPortal/Property/Recycling/xxxxxxxxxx')
req.add_header('User-Agent', user_agent)

fp = urlopen(req).read()

page = fp.decode("utf8")

soup = BeautifulSoup(page, features="html.parser")
soup.prettify()

#Form a JSON wrapper
data = {"bins":[]}
for element in soup.find_all("strong"):

    binType = element.next_element
    binType = binType.lstrip()
    collectionDate = element.next_sibling.next_element.next_element
   
   
    dict_data = {
     "type": binType,
     "collectionDate": collectionDate,
    }
    data["bins"].append(dict_data)

json_data = json.dumps(data, indent=4)

print(json_data)

