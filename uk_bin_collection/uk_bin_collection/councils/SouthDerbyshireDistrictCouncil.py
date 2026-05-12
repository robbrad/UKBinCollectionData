import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        data = {"bins": []}

        baseurl = "https://maps.southderbyshire.gov.uk/iShareLIVE.web//getdata.aspx?RequestType=LocalInfo&ms=mapsources/MyHouse&format=JSONP&group=Recycling%20Bins%20and%20Waste|Next%20Bin%20Collections&uid="
        url = baseurl + user_uprn

        requests.packages.urllib3.disable_warnings()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, verify=False, headers=headers).text

        jsonp_pattern = r"import\((\{.*\})\)"
        json_match = re.search(jsonp_pattern, response, re.S)

        if json_match:
            json_data = json_match.group(1)
            parsed_data = json.loads(json_data)
            html_content = parsed_data["Results"]["Next_Bin_Collections"]["_"]

            matches = re.findall(
                r"<span.*?>(\d{2} \w+ \d{4})</span>.*?<span.*?>(.*?)</span>",
                html_content,
                re.S,
            )

            for match in matches:
                dict_data = {
                    "type": match[1],
                    "collectionDate": datetime.strptime(
                        match[0], "%d %B %Y"
                    ).strftime("%d/%m/%Y"),
                }
                data["bins"].append(dict_data)

        return data
