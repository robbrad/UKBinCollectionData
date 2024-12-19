from bs4 import BeautifulSoup
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
        data = {"bins": []}
        collections = []

        user_postcode = kwargs.get("postcode")
        user_uprn = kwargs.get("uprn")

        check_uprn(user_uprn)
        check_postcode(user_postcode)

        headers = {
            "authority": "www.rugby.gov.uk",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-GB,en;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded",
            # 'cookie': 'JSESSIONID=7E90CAB54B649C3DCC7F6B5DA0897C63; COOKIE_SUPPORT=true; GUEST_LANGUAGE_ID=en_GB; AWSELB=D941E98916B5759862ED6C39DA9FB3FD9880491851D200C98112ABEC3223D52B19A2A2C6B37A89D3650D44FA5728FCAFEDE7BB2592D948FFF9C7B18D76C41AF02C308B0F3A2DE17F1585E9959BCE68CC83BC3AC753; CookieControl={"necessaryCookies":[],"optionalCookies":{},"statement":{},"consentDate":1701710876715,"consentExpiry":90,"interactedWith":true,"user":"8FED8810-3C3E-4D50-A9DC-42655030B3B1"}',
            "origin": "https://www.rugby.gov.uk",
            "pragma": "no-cache",
            "referer": "https://www.rugby.gov.uk/check-your-next-bin-day",
            "sec-ch-ua": '"Chromium";v="118", "Opera GX";v="104", "Not=A?Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.118 Safari/537.36",
        }
        params = {
            "p_p_id": "com_placecube_digitalplace_local_waste_portlet_CollectionDayFinderPortlet",
            "p_p_lifecycle": "0",
            "p_p_state": "normal",
            "p_p_mode": "view",
            "_com_placecube_digitalplace_local_waste_portlet_CollectionDayFinderPortlet_mvcRenderCommandName": "/collection_day_finder/get_days",
        }
        data = {
            "_com_placecube_digitalplace_local_waste_portlet_CollectionDayFinderPortlet_formDate": f"{datetime.now().timestamp().__floor__()}",
            "_com_placecube_digitalplace_local_waste_portlet_CollectionDayFinderPortlet_postcode": f"{user_postcode}",
            "_com_placecube_digitalplace_local_waste_portlet_CollectionDayFinderPortlet_uprn": f"{user_uprn}",
        }

        response = requests.post(
            "https://www.rugby.gov.uk/check-your-next-bin-day",
            params=params,
            headers=headers,
            data=data,
        )

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        table_rows = soup.find("table", {"class": "table"}).find("tbody").find_all("tr")

        for row in table_rows:
            row_text = row.text.strip().split("\n")
            bin_text = row_text[0].split(" ")
            bin_type = ' '.join(bin_text[1:]).capitalize()
            collections.append(
                (bin_type, datetime.strptime(row_text[1], "%A %d %b %Y"))
            )
            collections.append(
                (bin_type, datetime.strptime(row_text[3], "%A %d %b %Y"))
            )

        ordered_data = sorted(collections, key=lambda x: x[1])
        data = {"bins": []}
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
