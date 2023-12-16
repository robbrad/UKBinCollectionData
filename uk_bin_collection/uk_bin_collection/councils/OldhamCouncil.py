from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass

from bs4 import BeautifulSoup


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:

        data = {"bins": []}
        soup = BeautifulSoup(page.text, 'html.parser')

        # Find all tables with the class "data-table confirmation"
        tables = soup.find_all('table', class_='data-table confirmation')
        for table in tables:
            rows = table.find_all('tr')
            bin_type = None
            bin_collection = None

            # Search for the bin color in the table headers
            th_element = table.find('th')
            if th_element:
                bin_type = th_element.text.strip()

            for row in rows:
                header = row.find('b')
                if header:
                    header_text = header.text.strip()
                    value_cell = row.find('td', class_='coltwo')
                    if value_cell:
                        value_text = value_cell.text.strip()

                        if header_text == 'Collection Date':
                            bin_collection = value_text

            if bin_type and bin_collection:
                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(bin_collection, "%d/%m/%Y").strftime(date_format)
                }

                data["bins"].append(dict_data)

        return data
