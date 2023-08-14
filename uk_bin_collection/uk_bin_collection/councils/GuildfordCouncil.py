import requests
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

        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        url = "https://my.guildford.gov.uk/customers/s/sfsites/aura?r=15&other.BinScheduleDisplayCmp.GetBinSchedules=1"

        payload = 'message=%7B%22actions%22%3A%5B%7B%22id%22%3A%22250%3Ba%22%2C%22descriptor%22%3A%22apex%3A%2F' \
                  '%2FBinScheduleDisplayCmpController%2FACTION%24GetBinSchedules%22%2C%22callingDescriptor%22%3A' \
                  '%22markup%3A%2F%2Fc%3ABinScheduleDisplay%22%2C%22params%22%3A%7B%22database%22%3A%22domestic%22%2C' \
                  '%22UPRN%22%3A%22' + uprn + '%22%7D%2C%22version%22%3Anull%7D%5D%7D&aura.pageURI=%2Fcustomers%2Fs' \
                  '%2Fview-bin-collections&aura.context=%7B%22mode%22%3A%22PROD%22%2C%22fwuid%22%3A' \
                  '%22MlRqRU5YT3pjWFRNenJranFOMWFjQXlMaWFpdmxPSTZWeEo0bWtiN0hsaXcyNDQuMjAuNC0yLjQxLjQ%22%2C%22app%22' \
                  '%3A%22siteforce%3AcommunityApp%22%2C%22loaded%22%3A%7B%22APPLICATION%40markup%3A%2F%2Fsiteforce' \
                  '%3AcommunityApp%22%3A%22AHt2_xNq0mJPYC9ylIE4Ew%22%2C%22COMPONENT%40markup%3A%2F%2Finstrumentation' \
                  '%3Ao11ySecondaryLoader%22%3A%22WAlywPtXLxVWA9DxV-jd3A%22%2C%22COMPONENT%40markup%3A%2F' \
                  '%2Fflowruntime%3AflowRuntimeForFlexiPage%22%3A%22yd5ERlPoICEJEMf8W3eIXQ%22%7D%2C%22dn%22%3A%5B%5D' \
                  '%2C%22globals%22%3A%7B%7D%2C%22uad%22%3Afalse%7D&aura.token=null'

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Cookie': 'CookieConsentPolicy=0:1; LSKey-c$CookieConsentPolicy=0:1;'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        if response.status_code != 200:
            raise SystemError("Error retrieving data! Please try again or raise an issue on GitHub!")

        results = json.loads(response.text)

        if results["actions"][0]["state"] == "ERROR":
            raise ValueError("No collection data found for provided UPRN.")

        data = {"bins": []}

        schedules = results["actions"][0]["returnValue"]["FeatureSchedules"]

        for collection in schedules:
            bin_type = collection["FeatureName"]
            bin_collection = datetime.strptime(collection["NextDate"], "%Y-%m-%dT%H:%M:%S.%fZ")
            bin_previous_collection = datetime.strptime(collection["PreviousDate"], "%Y-%m-%dT%H:%M:%S.%fZ")
            if bin_collection:
                dict_data = {
                    "type": bin_type,
                    "collectionDate": bin_collection.strftime(date_format),
                    "previousCollectionDate": bin_previous_collection.strftime(date_format)
                }
                data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
