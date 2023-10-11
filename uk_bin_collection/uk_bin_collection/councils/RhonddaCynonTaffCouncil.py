from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        # Get UPRN from kwargs
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        # Construct headers and set passed UPRN as a param for request
        headers = {
            'authority': 'www.rctcbc.gov.uk',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-GB,en;q=0.9',
            'cache-control': 'no-cache',
            # 'cookie': 'ASP.NET_SessionId=2b4gaaydt1rlu5pccgrpzamm',
            'pragma': 'no-cache',
            'referer': 'https://www.rctcbc.gov.uk/EN/Resident/RecyclingandWaste/RecyclingandWasteCollectionDays.aspx?PropertyNumber=&Postcode=CF72%209JD',
            'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Opera GX";v="102"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36',
        }
        params = {
            'uprn': user_uprn,
        }

        response = requests.get(
            'https://www.rctcbc.gov.uk/EN/Resident/RecyclingandWaste/RecyclingandWasteCollectionDays.aspx',
            params=params,
            headers=headers,
        )

        # Throw an error if response is not HTTP200
        if response.status_code != 200:
            raise SystemError("Response status was not 200: Please raise an issue on GitHub!")

        # Parse response page and get all table rows
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()
        table_rows = soup.find("table", class_=("waste-table")).find_all("tr")

        # Find the bin type and parse the date for each row, then add to dict. First row will be just headings,
        # so skip it
        for row in table_rows:
            if len(row.contents) > 3:
                continue
            bin_type = row.contents[1].text.strip()
            bin_date_text = row.contents[2].text.split(',')[1].strip().replace(' of ', "")
            bin_date = datetime.strptime(remove_ordinal_indicator_from_date_string(bin_date_text),
                                         "%A %d %B %Y").strftime(date_format)

            dict_data = {
                "type": bin_type,
                "collectionDate": bin_date,
            }
            data["bins"].append(dict_data)

        return data
