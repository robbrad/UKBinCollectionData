#!/usr/bin/env python3
from urllib.request import Request, urlopen
import json
from bs4 import BeautifulSoup
from datetime import datetime

user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
headers = {'User-Agent': user_agent}

#Replace URL
req = Request('https://community.newcastle.gov.uk/my-neighbourhood/ajax/getBinsNew.php?uprn=XXXXXXXXXXXX')
req.add_header('User-Agent', user_agent)

fp = urlopen(req).read()
page = fp.decode("utf8")

soup = BeautifulSoup(page, features="html.parser")
soup.prettify()

#Form a JSON wrapper
data = {"bins":[]}

#Loops the strong elements
for element in soup.find_all("strong"):
    #Domestic Waste is formatted differenty to other bins
    if "Green Bin (Domestic Waste) details:" in str(element):
        collectionInfo = element.next_sibling.find('br').next_element
    else:
        collectionInfo = element.next_sibling.next_sibling.next_sibling.next_sibling
    
    binType = str(element)[str(element).find("(")+1:str(element).find(")")]
    collectionDate = str(datetime.strptime(str(collectionInfo).replace('Next collection : ',''), '%d-%b-%Y').date())
    
    dict_data = {
        "BinType": binType,
        "NextCollectionDate": collectionDate
        }

    #Add data to the main JSON Wrapper
    data["bins"].append(dict_data)


##Make the JSON
json_data = json.dumps(data,sort_keys=True, indent=4)

print(json_data)