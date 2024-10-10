import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


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
        data = {"bins": []}

        baseurl = "https://maps.southderbyshire.gov.uk/iShareLIVE.web//getdata.aspx?RequestType=LocalInfo&ms=mapsources/MyHouse&format=JSONP&group=Recycling%20Bins%20and%20Waste|Next%20Bin%20Collections&uid="
        url = baseurl + user_uprn

        # Make the web request
        response = requests.get(url).text

        # Remove the JSONP wrapper using a regular expression
        jsonp_pattern = r"\{.*\}"
        json_match = re.search(jsonp_pattern, response)

        if json_match:
            # Extract the JSON part
            json_data = json_match.group(0)

            # Parse the JSON
            parsed_data = json.loads(json_data)

            # Extract the embedded HTML string
            html_content = parsed_data["Results"]["Next_Bin_Collections"]["_"]

            # Parse the HTML to extract dates and bin types using regex
            matches = re.findall(
                r"<span.*?>(\d{2} \w+ \d{4})</span>.*?<span.*?>(.*?)</span>",
                html_content,
                re.S,
            )

            # Output the parsed bin collection details
            for match in matches:
                dict_data = {
                    "type": match[1],
                    "collectionDate": datetime.strptime(match[0], "%d %B %Y").strftime(
                        "%d/%m/%Y"
                    ),
                }
                data["bins"].append(dict_data)
        else:
            print("No valid JSON found in the response.")

        return data
