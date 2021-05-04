#!/usr/bin/env python3
from urllib.request import Request, urlopen
import json
from bs4 import BeautifulSoup

payload={}

# Charnwood uses a cookie to determine the location for the request which has a unique id for your property along with the address
# For this reason it cannot be programatically populated
# go to my.charnwood.gov.uk and search for your address, then inspect your cookie for the website and take the 'my_location' value and populate into the parameter below
my_location = 'xxxxxx'

req = Request('https://my.charnwood.gov.uk/')
req.add_header('cookie', f'my_location={my_location}')
req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; Win64; x64)')

fp = urlopen(req).read()
page = fp.decode("utf8")

soup = BeautifulSoup(page, features="html.parser")
soup.prettify()

data = {"bins":[]}

for bins in soup.findAll("ul", {"class" : 'refuse'}):

    binCollection = bins.find_all('li')

    if binCollection:
      for bin in binCollection:
          dict_data = {
           "CollectionDate": bin.find("strong", {"class" : 'date'}).contents[0],
           "BinType": bin.find("a").contents[0],
          }

          data["bins"].append(dict_data)

json_data = json.dumps(data)

print(json_data)
