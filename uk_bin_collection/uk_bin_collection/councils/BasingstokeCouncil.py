from bs4 import BeautifulSoup
from datetime import datetime
import requests
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass

COLLECTION_KINDS = {
    "waste": "rteelem_ctl03_pnlCollections_Refuse",
    "recycling": "rteelem_ctl03_pnlCollections_Recycling",
    "glass": "rteelem_ctl03_pnlCollections_Glass",
    # Garden waste data is only returned if the property is subscribed to the Garden Waste service
    "garden": "rteelem_ctl03_pnlCollections_GardenWaste"
}


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        requests.packages.urllib3.disable_warnings()

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        cookies = {
            'cookie_control_popup': 'A',
            'WhenAreMyBinsCollected': f'{user_uprn}',
        }

        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://www.basingstoke.gov.uk',
            'Pragma': 'no-cache',
            'Referer': 'https://www.basingstoke.gov.uk/rte.aspx?id=1270',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36',
            'X-MicrosoftAjax': 'Delta=true',
            'X-Requested-With': 'XMLHttpRequest',
        }

        params = {
            'id': '1270',
        }

        data = f'rteelem%24ctl03%24ctl00=rteelem%24ctl03%24ctl01%7Crteelem%24ctl03%24gapAddress%24ctl05&rteelem%24ctl03%24gapAddress%24lstStage2_SearchResults=UPRN%3A{user_uprn}&__EVENTTARGET=rteelem%24ctl03%24gapAddress%24ctl05&__EVENTARGUMENT=&__VIEWSTATE=%2FwEPDwUKLTQ2NzE5Mjc0NQ9kFgJmD2QWAgICD2QWAgIBD2QWAgIHD2QWAmYPZBYEAgEPDxYEHhNBc3NvY2lhdGVkQ29udHJvbElEBSJnYXBBZGRyZXNzOmxzdFN0YWdlMl9TZWFyY2hSZXN1bHRzHgRUZXh0BQ5TZWxlY3QgYWRkcmVzc2RkAgMPDxYEHiBHYXBFeHRlcm5hbFByb21wdExhYmVsVGV4dFN0YWdlMQUSU2VhcmNoIGZvciBhZGRyZXNzHiBHYXBFeHRlcm5hbFByb21wdExhYmVsVGV4dFN0YWdlMgUOU2VsZWN0IGFkZHJlc3NkFgJmD2QWBGYPDxYCHgdWaXNpYmxlaGQWAmYPDxYCHwEFCFJHMjIgNlRIZGQCAQ8PFgIfBGdkFgJmDxBkEBUMNDEzOCBTdCBQZXRlcnMgUm9hZCwgQmFzaW5nc3Rva2UsIEhhbXBzaGlyZSwgUkcyMiA2VEg0MTQwIFN0IFBldGVycyBSb2FkLCBCYXNpbmdzdG9rZSwgSGFtcHNoaXJlLCBSRzIyIDZUSDQxNDIgU3QgUGV0ZXJzIFJvYWQsIEJhc2luZ3N0b2tlLCBIYW1wc2hpcmUsIFJHMjIgNlRINDE0NCBTdCBQZXRlcnMgUm9hZCwgQmFzaW5nc3Rva2UsIEhhbXBzaGlyZSwgUkcyMiA2VEg0MTQ2IFN0IFBldGVycyBSb2FkLCBCYXNpbmdzdG9rZSwgSGFtcHNoaXJlLCBSRzIyIDZUSDQxNDggU3QgUGV0ZXJzIFJvYWQsIEJhc2luZ3N0b2tlLCBIYW1wc2hpcmUsIFJHMjIgNlRINDE1MCBTdCBQZXRlcnMgUm9hZCwgQmFzaW5nc3Rva2UsIEhhbXBzaGlyZSwgUkcyMiA2VEg0MTUyIFN0IFBldGVycyBSb2FkLCBCYXNpbmdzdG9rZSwgSGFtcHNoaXJlLCBSRzIyIDZUSDQxNTQgU3QgUGV0ZXJzIFJvYWQsIEJhc2luZ3N0b2tlLCBIYW1wc2hpcmUsIFJHMjIgNlRINDE1NiBTdCBQZXRlcnMgUm9hZCwgQmFzaW5nc3Rva2UsIEhhbXBzaGlyZSwgUkcyMiA2VEg0MTU4IFN0IFBldGVycyBSb2FkLCBCYXNpbmdzdG9rZSwgSGFtcHNoaXJlLCBSRzIyIDZUSDQxNjAgU3QgUGV0ZXJzIFJvYWQsIEJhc2luZ3N0b2tlLCBIYW1wc2hpcmUsIFJHMjIgNlRIFQwRVVBSTjoxMDAwNjAyNDM5MjcRVVBSTjoxMDAwNjAyNDM5MjkRVVBSTjoxMDAwNjAyNDM5MzERVVBSTjoxMDAwNjAyNDM5MzMRVVBSTjoxMDAwNjAyNDM5MzURVVBSTjoxMDAwNjAyNDM5MzYRVVBSTjoxMDAwNjAyNDM5MzcRVVBSTjoxMDAwNjAyNDM5MzgRVVBSTjoxMDAwNjAyNDM5MzkRVVBSTjoxMDAwNjAyNDM5NDARVVBSTjoxMDAwNjAyNDM5NDERVVBSTjoxMDAwNjAyNDM5NDIUKwMMZ2dnZ2dnZ2dnZ2dnZGRkpXCIF40J9nPqukmdVM4NgNZFZyw%3D&__VIEWSTATEGENERATOR=99691FF6&__EVENTVALIDATION=%2FwEdABCb2eofM0yrOZt2P3lnE8LBzdIwLRuYuP7lVS1GO2hXAAf%2FiyMIUYr%2BX38W%2FCsEufkYF%2FJqBocIUvPBZShq0SWLlDuEZpde9d1EPv1cdNAxtv0a5P%2BAzvWcKULA75C%2FHDNl8al%2FKtVDH8iZIW8%2BPWamtUNjyfZaTGu1VxFRW7%2BrIZHFk8PySEuoYzdlb%2Fw0NMLP8MZHHy%2BSyI7El1raMGfVGyh7Lv3Ohzid1s46Z3mtovjgyLnG9kXo%2FMyI4mgBTTdOYHrncJX8sN52g9M2NHMrNJrGEa%2BGwkZVSfqAxtisKhbq%2Bzxiu%2BV7mP9nRlRrnJ0yunAhZS1%2FkWU9mq7vbq4HclDPJK5tGeZ7jNpUx3wTgU%2Btyxc%3D&__ASYNCPOST=true&'

        response = requests.post('https://www.basingstoke.gov.uk/rte.aspx', params=params, cookies=cookies,
                                 headers=headers, data=data, verify=False)

        if response.status_code != 200:
            raise SystemError("Error retrieving data! Please try again or raise an issue on GitHub!")

        # Make a BS4 object
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        bins = []

        for collection_type, collection_class in COLLECTION_KINDS.items():
            for date in soup.select(f"div#{collection_class} li"):
                bins.append({
                    "type": collection_type,
                    "collectionDate": datetime.strptime(
                        # Friday, 21 July 2023
                        date.get_text(strip=True),
                        '%A, %d %B %Y'
                    ).strftime(date_format)
                })

        return {
            "bins": bins
        }
