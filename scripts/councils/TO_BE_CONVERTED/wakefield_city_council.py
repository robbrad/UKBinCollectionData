#!/usr/bin/env python3
from urllib.request import Request, urlopen
import json
from bs4 import BeautifulSoup

user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
headers = {'User-Agent': user_agent}

#Replace UPRN
req = Request('https://www.wakefield.gov.uk/site/Where-I-Live-Results?uprn=XXXXXXX')
req.add_header('User-Agent', user_agent)

fp = urlopen(req).read()

page = fp.decode("utf8")

soup = BeautifulSoup(page, features="html.parser")
soup.prettify()

#Form a JSON wrapper
data = {"bins":[]}

for bins in soup.findAll("div", {"class" : lambda L: L and L.startswith('mb10 ind-waste-')}):

    #Get the type of bin
    binTypes = bins.find_all("div", {"class" : 'mb10'})
    binType = binTypes[0].get_text(strip=True)

    #Find the collection dates
    binCollections = bins.find_all("div", {"class" : lambda L: L and L.startswith('col-sm-4')})


    if binCollections:
        lastCollections = binCollections[0].find_all("div")
        nextCollections = binCollections[1].find_all("div")

        #Get the collection date
        lastCollection = lastCollections[1].get_text(strip=True)
        nextCollection = nextCollections[1].get_text(strip=True)

        if lastCollection:
            dict_data = {
             "BinType": binType,
             "Last Collection Date": lastCollection,
             "Next Collection Date": nextCollection
            }

            data["bins"].append(dict_data)

json_data = json.dumps(data)

print(json_data)
