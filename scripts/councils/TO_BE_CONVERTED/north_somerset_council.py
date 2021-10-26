#!/usr/bin/env python3
import requests
import re
import json
from bs4 import BeautifulSoup

user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
headers = {'User-Agent': user_agent}

url = 'https://forms.n-somerset.gov.uk/Waste/CollectionSchedule'
values = {'PreviousHouse' : '',
          'PreviousPostcode' : 'x',
          'Postcode' : 'x',
          'SelectedUprn' : 'XXXXXXXXXX' }

req = requests.post(url, values, headers=headers)

soup = BeautifulSoup(req.text, features="html.parser")

rows = soup.find("table", {'class': re.compile('table')}).find_all("tr")

#Form a JSON wrapper
data = {"bins":[]}

#Loops the Rows
for row in rows:
    cells = row.find_all("td")
    if cells: 
        binType = cells[0].get_text(strip=True)
        collectionDate = cells[1].get_text(strip=True)
        nextCollectionDate = cells[2].get_text(strip=True)

        #Make each Bin element in the JSON
        dict_data = {
        "BinType": binType,
        "collectionDate": collectionDate,
        "nextCollectionDate": nextCollectionDate
        }

        #Add data to the main JSON Wrapper
        data["bins"].append(dict_data)

##Make the JSON
json_data = json.dumps(data,sort_keys=True, indent=4)

#Output the data - run this script with a redirect to send the output to a file
#Suggest Crontab
print(json_data)
