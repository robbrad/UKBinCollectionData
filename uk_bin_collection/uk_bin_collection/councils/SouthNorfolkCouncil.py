from bs4 import BeautifulSoup
from xml.etree import ElementTree

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    baseclass. They can also override some
    operations with a default implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)
        council = "SNO"

        # Make SOAP request
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "text/xml; charset=UTF-8",
            "Host": "collections-southnorfolk.azurewebsites.net",
            "Origin": "https://collections-southnorfolk.azurewebsites.net",
            "Referer": "https://collections-southnorfolk.azurewebsites.net/calendar.html",
            "sec-ch-ua": '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        }
        requests.packages.urllib3.disable_warnings()
        post_data = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            '<soap:Body><getRoundCalendarForUPRN xmlns="http://webaspx-collections.azurewebsites.net/">'
            "<council>" + council + "</council><UPRN>" + uprn + "</UPRN>"
            "<from>Chtml</from></getRoundCalendarForUPRN></soap:Body></soap:Envelope>"
        )
        response = requests.post(
            "https://collections-southnorfolk.azurewebsites.net/WSCollExternal.asmx",
            headers=headers,
            data=post_data,
        )
        if response.status_code != 200:
            raise ValueError("No bin data found for provided UPRN.")

        # Get HTML from SOAP response
        xmltree = ElementTree.fromstring(response.text)
        html = xmltree.find(
            ".//{http://webaspx-collections.azurewebsites.net/}getRoundCalendarForUPRNResult"
        ).text
        # Parse with BS4
        soup = BeautifulSoup(html, features="html.parser")
        soup.prettify()

        data = {"bins": []}
        for bin_type in ["RefuseBin", "RecycleBin", "GardenBin"]:
            bin_el = soup.find("b", text=bin_type)
            if bin_el:
                bin_info = bin_el.next_sibling.split(": ")[1]
                collection_date = ""
                results = re.search("([A-Za-z]+ \d\d? [A-Za-z]+) then", bin_info)
                if results:
                    date = datetime.strptime(
                        results[1] + " " + datetime.now().strftime("%Y"), "%a %d %b %Y"
                    )
                    if date:
                        collection_date = date.strftime(date_format)
                else:
                    results2 = re.search("([A-Za-z]+) then", bin_info)
                    if results2:
                        collection_date = results2[1]

                if collection_date != "":
                    dict_data = {
                        "type": bin_type,
                        "collectionDate": collection_date,
                    }
                    data["bins"].append(dict_data)

        return data
