from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)

        data = {"bins": []}

        # Start a new session
        requests.packages.urllib3.disable_warnings()
        s = requests.session()

        headers = {
            'authority': 'www.bolton.gov.uk',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-GB,en;q=0.9',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.bolton.gov.uk',
            'pragma': 'no-cache',
            'referer': 'https://www.bolton.gov.uk/next-bin-collection',
            'sec-ch-ua': '"Not?A_Brand";v="99", "Opera GX";v="97", "Chromium";v="111"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.5563.147 Safari/537.36',
        }
        
        # Get our initial session running
        response = s.get("https://carehomes.bolton.gov.uk/bins.aspx", headers=headers)

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        # Grab the variables needed to continue
        payload = {
            "__VIEWSTATE": (
                soup.find("input", {"id": "__VIEWSTATE"}).get("value")
            ),
            "__VIEWSTATEGENERATOR": (
                soup.find("input", {"id": "__VIEWSTATEGENERATOR"}).get("value")
            ),
            "__EVENTVALIDATION": (
                soup.find("input", {"id": "__EVENTVALIDATION"}).get("value")
            ),
            "txtPostcode": (user_postcode),
            "btnSubmit": "Submit"
        }

        # Get the address selection page
        response = s.post("https://carehomes.bolton.gov.uk/bins.aspx", data=payload, headers=headers)

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        # Grab the variables needed to continue
        payload = {
            "__VIEWSTATE": (
                soup.find("input", {"id": "__VIEWSTATE"}).get("value")
            ),
            "__VIEWSTATEGENERATOR": (
                soup.find("input", {"id": "__VIEWSTATEGENERATOR"}).get("value")
            ),
            "__EVENTVALIDATION": (
                soup.find("input", {"id": "__EVENTVALIDATION"}).get("value")
            ),
            "txtPostcode": (user_postcode),
            "ddlAddresses": (user_uprn)
        }

        # Get the final page with the actual bin data
        response = s.post("https://carehomes.bolton.gov.uk/bins.aspx", data=payload, headers=headers)

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        collections = []

        # Find section with bins in
        sections = soup.find_all("div", {"class": "bin-info"})

        # For each bin section, get the text and the list elements
        for item in sections:
            words = item.find_next("strong").text.split()[2:4]
            bin_type = ' '.join(words).capitalize()
            date_list = item.find_all("p")
            for d in date_list:
                next_collection = datetime.strptime(d.text.strip(), "%A %d %B %Y")
                collections.append((bin_type, next_collection))

        # Sort the text and list elements by date
        ordered_data = sorted(collections, key=lambda x: x[1])

        # Put the elements into the dictionary
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data

