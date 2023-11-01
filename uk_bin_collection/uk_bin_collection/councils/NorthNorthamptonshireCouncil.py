import hashlib
import math
import time
from datetime import datetime as dtm, timedelta

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


def myFunc(e):
  return e['start']

class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}
        uprn = kwargs.get("uprn")
        check_uprn(uprn)
        today = int(datetime.now().timestamp())*1000
        dateforurl = datetime.now().strftime("%Y-%m-%d")
        dateforurl2 = (datetime.now() + timedelta(days=42)).strftime("%Y-%m-%d")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)",
        }
        requests.packages.urllib3.disable_warnings()
        
        # Get variables for workings
        response = requests.get(
            f"https://cms.northnorthants.gov.uk/bin-collection-search/calendarevents/{uprn}/{dateforurl}/{dateforurl2}",
            headers=headers,
        )
        if response.status_code != 200:
            raise ValueError("No bin data found for provided UPRN..")

        json_response = json.loads(response.text)

        output_dict = [x for x in json_response if int(''.join(filter(str.isdigit, x['start']))) >= today]
		
        output_json = output_dict
        output_json.sort(key=myFunc)

        i = 0
        while i < len(output_json):
            sov = output_json[i]['title'].lower()
            if 'recycling' in sov:
                bin_type = "Recycling"
            elif 'garden' in sov:
                bin_type = "Garden"
            elif 'refuse' in sov:
                bin_type = "General"
            else:
                bin_type = "Unknown"
            dateofbin = int(''.join(filter(str.isdigit, output_json[i]['start'])))
            day = dtm.fromtimestamp(dateofbin/1000)
            collection_data = {
                "type": bin_type,
                "collectionDate": day.strftime(date_format),
            }
            data["bins"].append(collection_data)
            i += 1

        return data