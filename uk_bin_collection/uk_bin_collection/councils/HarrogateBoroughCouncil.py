from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        headers = {
            'accept-language': 'en-GB,en;q=0.9',
            'cache-control': 'no-cache',
            }

        req_data = {
            'uprn': user_uprn,
        }

        url = f'https://secure.harrogate.gov.uk/inmyarea/Property/?uprn={user_uprn}'

        requests.packages.urllib3.disable_warnings()
        response = requests.post(url, headers=headers)

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        collections = []

        # Find section with bins in
        table = soup.find_all("table", {"class": "hbcRounds"})[1]

        # For each bin section, get the text and the list elements
        for row in table.find_all('tr'):
            bin_type = row.find('th').text
            td = row.find('td')
            for span in td.find_all('span'):
                span.extract()
            collectionDate = td.text.strip()
            next_collection = datetime.strptime(collectionDate, "%a %d %b %Y")
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
