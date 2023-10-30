from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass
import re

# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """


    def parse_data(self, page: str, **kwargs) -> dict:
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()
        
        regex_pattern = r'<li>([^<]+)<'
        
        data = {"bins": []}

        for bins in soup.select('div[class*="containererf"]'):
            
            collection_date = datetime.strptime(bins.find(id="content").text.strip(), "%A, %d/%m/%Y")
            bin_type_div = bins.find(id='main1')
            bin_types = bin_type_div.findAll('li')
            for bin_type in bin_types:

                bin_type_name = re.sub(r'\(.*\)', '', bin_type.text).strip()

                dict_data = {
                    "type": bin_type_name,
                    "collectionDate": collection_date.strftime(date_format)
                }
                data["bins"].append(dict_data)

        return data
