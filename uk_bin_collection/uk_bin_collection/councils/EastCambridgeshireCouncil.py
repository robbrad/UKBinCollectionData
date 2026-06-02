from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        url = f"https://eastcambs-self.achieveservice.com/appshost/firmstep/self/apps/custompage/bincollections?language=en&uprn={uprn}"

        requests.packages.urllib3.disable_warnings()
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        # Session priming — required since site update
        s.get("https://eastcambs-self.achieveservice.com/bincollections", timeout=30)

        page = s.get(url, timeout=30)

        soup = BeautifulSoup(page.text, features="html.parser")
        data = {"bins": []}

        for bins in soup.find_all("div", {"class": "row collectionsrow"}):
            divs = bins.find_all("div")
            if len(divs) < 3:
                continue
            _, bin_type_div, date_div = divs[:3]
            bin_type = bin_type_div.text.strip()
            date_text = date_div.text.strip()
            if not bin_type or not date_text:
                continue
            date = datetime.strptime(date_text, "%a - %d %b %Y").date()
            data["bins"].append(
                {"type": bin_type, "collectionDate": date.strftime(date_format)}
            )

        return data
