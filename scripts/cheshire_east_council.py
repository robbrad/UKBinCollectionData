#!/usr/bin/env python3

#This script pulls (in one hit) the data from Cheshire East Council Bins Data

import json
import re
#import the wonderful Beautiful Soup and the URL grabber
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

#Set a user agent so we look like a browser ;-)
user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
headers = {'User-Agent': user_agent}

#Make the Request - change the URL
req = Request('https://online.cheshireeast.gov.uk/MyCollectionDay/SearchByAjax/GetBartecJobList?uprn=XXXXXXXXXXX&onelineaddress=XXXXXX&_=XXXXXX')
req.add_header('User-Agent', user_agent)
fp = urlopen(req).read()

#decode the page
page = fp.decode("utf8")

#Make a BS4 object
soup = BeautifulSoup(page, features="html.parser")
soup.prettify()

#Form a JSON wrapper
data = {"bins":[]}

#Search for the specific table using BS4
rows = soup.find("table", {'class': re.compile('job-details')}).find_all("tr", {'class': re.compile('data-row')})

#Loops the Rows
for row in rows:
    cells = row.find_all("td", {"class" : lambda L: L and L.startswith('visible-cell')})

    labels = cells[0].find_all("label")
    binType = labels[2].get_text(strip=True)
    collectionDate = labels[1].get_text(strip=True)

    #Make each Bin element in the JSON
    dict_data = {
     "BinType": binType,
     "collectionDate": collectionDate,
    }

    #Add data to the main JSON Wrapper
    data["bins"].append(dict_data)

##Make the JSON
json_data = json.dumps(data,sort_keys=True, indent=4)

#Output the data - run this script with a redirect to send the output to a file
#Suggest Crontab
print(json_data)
