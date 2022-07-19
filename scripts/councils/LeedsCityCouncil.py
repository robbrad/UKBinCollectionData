# This script pulls (in one hit) the data
# from Warick District Council Bins Data
import os
import shutil
import tempfile

from get_bin_data import AbstractGetBinDataClass

import csv
import urllib.request


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str) -> dict:
        user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
        headers = {"User-Agent": user_agent}

        address_csv_url = "https://opendata.leeds.gov.uk/downloads/bins/dm_premises.csv"
        collections_csv_url = "https://opendata.leeds.gov.uk/downloads/bins/dm_jobs.csv"

        with urllib.request.urlopen(address_csv_url) as response:
            with tempfile.NamedTemporaryFile(delete=False) as address_file:
                shutil.copyfileobj(response, address_file)

        with urllib.request.urlopen(collections_csv_url) as response:
            with tempfile.NamedTemporaryFile(delete=False) as collections_file:
                shutil.copyfileobj(response, collections_file)

        print(address_file.name)

        # address_response = requests.get(address_csv_url)
        # addresses_text = address_response.iter_lines()
        # addresses_csv = csv.reader(addresses_text, delimiter=',')
        #
        # collections_response = requests.get(collections_csv_url)
        # collections_text = collections_response.iter_lines()
        # collections_csv = csv.reader(collections_text, delimiter=',')

        data = {"bins": []}

        os.remove(address_file)
        os.remove(collections_file)
        return data
