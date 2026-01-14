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
        # Disable the SSL warnings that otherwise break everything
        requests.packages.urllib3.disable_warnings()
        try:
            requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS += (
                ":HIGH:!DH:!aNULL"
            )
        except AttributeError:
            pass

        # UPRN is street id here
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        data = {"bins": []}

        base_url = "https://apps.castlepoint.gov.uk/cpapps/"

        post_url = f"{base_url}index.cfm?fa=myStreet.displayDetails"
        post_header_str = (
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
            "image/apng,"
            "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9|Accept-Encoding: gzip, deflate, "
            "br|Accept-Language: en-GB;q=0.8|Cache-Control: max-age=0|Connection: "
            "keep-alive|Content-Length: "
            "11|Content-Type: application/x-www-form-urlencoded|Host: apps.castlepoint.gov.uk|Origin: "
            "https://apps.castlepoint.gov.uk|Referer: "
            "https://apps.castlepoint.gov.uk/cpapps/index.cfm?fa=wastecalendar|Sec-Fetch-Dest: "
            "document|Sec-Fetch-Mode: navigate|Sec-Fetch-Site: same-origin|Sec-Fetch-User: ?1|Sec-GPC: "
            "1|Upgrade-Insecure-Requests: 1|User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36 "
        )

        post_headers = parse_header(post_header_str)
        form_data = {"roadID": uprn}
        post_response = requests.post(
            post_url, headers=post_headers, data=form_data, verify=False
        )

        # Make a BS4 object
        soup = BeautifulSoup(post_response.text, features="html.parser")
        soup.prettify()

        wasteCalendarContainer = soup.find("div", class_="contentContainer")
        if not wasteCalendarContainer:
            return data
        year_txt = wasteCalendarContainer.find("h1").get_text(strip=True)
        year = datetime.strptime(year_txt, "About my Street - %B %Y").strftime("%Y")

        calendarContainer = soup.find("div", class_="calendarContainer")
        if not calendarContainer:
            return data
        calendarContainer2 = calendarContainer.find_all(
            "div", class_="calendarContainer"
        )

        for container in calendarContainer2:
            table = container.find("table", class_="calendar")
            if not table:
                continue
            month_txt = container.find("tr", class_="calendar").get_text(strip=True)
            month = datetime.strptime(month_txt, "%B").strftime("%m")
            print(month_txt)

            pink_days = [
                td.get_text(strip=True)
                for td in table.find_all("td", class_="pink")
                if td.get_text(strip=True)
            ]
            normal_days = [
                td.get_text(strip=True)
                for td in table.find_all("td", class_="normal")
                if td.get_text(strip=True)
            ]

            for day in pink_days:
                dict_data = {
                    "type": "Pink collection",
                    "collectionDate": datetime(
                        year=int(year), month=int(month), day=int(day)
                    ).strftime(date_format),
                }
                data["bins"].append(dict_data)
            for day in normal_days:
                dict_data = {
                    "type": "Normal collection",
                    "collectionDate": datetime(
                        year=int(year), month=int(month), day=int(day)
                    ).strftime(date_format),
                }
                data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return data
