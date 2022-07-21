# This script pulls (in one hit) the data
# from Warick District Council Bins Data
import os
from datetime import datetime
import pandas as pd
from get_bin_data import AbstractGetBinDataClass
import urllib.request


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
        headers = {"User-Agent": user_agent}

        # URLs to data sources
        address_csv_url = "https://opendata.leeds.gov.uk/downloads/bins/dm_premises.csv"
        collections_csv_url = "https://opendata.leeds.gov.uk/downloads/bins/dm_jobs.csv"

        if kwargs.get("postcode") == "" or kwargs.get("postcode") is None:
            print("What is your postcode?")
            user_postcode = input("> ").replace(" ", "")
        else:
            user_postcode = kwargs.get("postcode").replace(" ", "")

        if kwargs.get("paon") == "" or kwargs.get("paon") is None:
            print("What is your house number/name?")
            user_paon = input("> ").replace(" ", "")
        else:
            user_paon = kwargs.get("paon").replace(" ", "")

        data: dict[datetime, str] = {}
        prop_id = 0

        # Get address csv and give it headers (pandas bypasses downloading the file)
        print("Getting address data...")
        with urllib.request.urlopen(address_csv_url) as response:
            addr = pd.read_csv(response, names=["PropertyId", "PropertyName", "PropertyNo", "Street",
                                                             "Town", "City", "Postcode"], sep=",")

        # Get collections csv and give it headers
        print("Getting collection data...")
        with urllib.request.urlopen(collections_csv_url) as response:
            coll = pd.read_csv(response, names=["PropertyId", "BinType", "CollectionDate"], sep=",")

        # Find the property id from the address data
        print("Finding property reference...")
        for row in addr.itertuples():
            if str(row.Postcode).replace(" ", "") == user_postcode:
                if row.PropertyNo == user_paon:
                    prop_id = row.PropertyId
                    print(f"Reference: {str(prop_id)}")
                    continue

        # For every match on the property id in the collections data, add the bin type and date to list
        # Note: time is 7am as that's when LCC ask bins to be out by
        job_list = []
        print(f"Finding collections for property reference: {user_paon}, {user_postcode}...")
        for row in coll.itertuples():
            if row.PropertyId == prop_id:
                time = datetime.strptime('070000', '%H%M%S').time()
                date_obj = datetime.strptime(row.CollectionDate, '%d/%m/%y')
                combined_date = datetime.combine(date_obj, time)
                job_list.append([row.BinType, combined_date])

        # If jobs exist, sort list by date order. Load list into dictionary to return
        print("Processing collections...")
        if len(job_list) > 0:
            job_list.sort(key=lambda x: (x[1]))
            for job in job_list:
                data.update({job[1].strftime("%d/%m/%y"): job[0]})
        else:
            print("No bin collections found for property!")

        return data
