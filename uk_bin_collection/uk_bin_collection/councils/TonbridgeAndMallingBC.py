from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from datetime import *
import requests


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:

        # Get UPRN and postcode from the parsed args
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)

        requests.packages.urllib3.disable_warnings()

        # Set up some form data, then POST for the form and scrape the result
        headers = {
            'Accept':                    'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language':           'en-GB,en;q=0.6',
            'Cache-Control':             'no-cache',
            'Connection':                'keep-alive',
            'Content-Type':              'multipart/form-data; boundary=----WebKitFormBoundaryI1XYcX9fNeKxm4LB',
            # 'Cookie': 'PHPSESSID=-3mn6j-vkWcY4xPPXbT3Ggk1gSQJLId%2CztSoQV5-f8Pi7Cju1wwE151qtwdUyE1c',
            'Origin':                    'https://www.tmbc.gov.uk',
            'Pragma':                    'no-cache',
            'Referer':                   'https://www.tmbc.gov.uk/xfp/form/167',
            'Sec-Fetch-Dest':            'document',
            'Sec-Fetch-Mode':            'navigate',
            'Sec-Fetch-Site':            'same-origin',
            'Sec-Fetch-User':            '?1',
            'Sec-GPC':                   '1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent':                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'sec-ch-ua':                 '"Not?A_Brand";v="8", "Chromium";v="108", "Brave";v="108"',
            'sec-ch-ua-mobile':          '?0',
            'sec-ch-ua-platform':        '"Windows"',
        }
        data = f'------WebKitFormBoundaryI1XYcX9fNeKxm4LB\r\nContent-Disposition: form-data; ' \
               f'name="__token"\r\n\r\ns_flSv1eIvJDeCwbFaYxclM3UTomdpWgg2cMWzZckaU\r\n' \
               f'------WebKitFormBoundaryI1XYcX9fNeKxm4LB\r\nContent-Disposition: form-data; ' \
               f'name="page"\r\n\r\n128\r\n------WebKitFormBoundaryI1XYcX9fNeKxm4LB\r\nContent-Disposition: ' \
               f'form-data; name="locale"\r\n\r\nen_GB\r\n------WebKitFormBoundaryI1XYcX9fNeKxm4LB\r\nContent' \
               f'-Disposition: form-data; name="q752eec300b2ffef2757e4536b77b07061842041a_0_0"\r\n\r\n' \
               f'{user_postcode}\r\n------WebKitFormBoundaryI1XYcX9fNeKxm4LB\r\nContent-Disposition: form-data; ' \
               f'name="q752eec300b2ffef2757e4536b77b07061842041a_1_0"\r\n\r\n' \
               f'{user_uprn}\r\n------WebKitFormBoundaryI1XYcX9fNeKxm4LB\r\nContent-Disposition: form-data; ' \
               f'name="next"\r\n\r\nNext\r\n------WebKitFormBoundaryI1XYcX9fNeKxm4LB--\r\n '

        response = requests.post('https://www.tmbc.gov.uk/xfp/form/167', headers=headers, data=data)
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}
        last_date = datetime.now()

        # Find the table on the page and get data from each row (we don't care about the headings)
        table = soup.find("table", {"class": "data-table waste-collections-table"}).find("tbody")
        for row in table.find_all("tr"):
            bin_date = row.find_next("td").text.strip()
            collection_types = row.find("div", {"class": "collections"}).find_all("p")

            # For each collection type in the list, parse the time
            for item in collection_types:
                curr_bin_date = datetime.strptime(bin_date, "%a %d %B")

                # The calendar doesn't include the year, so using this to try to mitigate year change (note: it's
                # currently January, so no idea if it will work until the end of the year lol)
                if last_date.date().isocalendar().week < 52:
                    curr_bin_date = datetime(last_date.year, curr_bin_date.month, curr_bin_date.day)
                else:
                    curr_bin_date = datetime(last_date.year + 1, curr_bin_date.month, curr_bin_date.day)

                # Add each collection to the dictionary
                dict_data = {
                    "type":           item.text.strip(),
                    "collectionDate": curr_bin_date.strftime(date_format)
                }
                data["bins"].append(dict_data)
                last_date = curr_bin_date

        return data
