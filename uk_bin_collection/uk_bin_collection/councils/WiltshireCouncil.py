import re

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        requests.packages.urllib3.disable_warnings()
        # Define some months to get from the calendar
        this_month = datetime.now().month
        this_year = datetime.now().year
        one_month = this_month + 1
        two_month = this_month + 2
        months = [this_month, one_month, two_month]

        # Get and check the postcode and UPRN values
        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        user_uprn = str(user_uprn).zfill(12)

        # Some data for the request
        cookies = {
            "ARRAffinity": "c5a9db7fe43cef907f06528c3d34a997365656f757206fbdf34193e2c3b6f737",
            "ARRAffinitySameSite": "c5a9db7fe43cef907f06528c3d34a997365656f757206fbdf34193e2c3b6f737",
        }
        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-GB,en;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            # 'Cookie': 'ARRAffinity=c5a9db7fe43cef907f06528c3d34a997365656f757206fbdf34193e2c3b6f737; ARRAffinitySameSite=c5a9db7fe43cef907f06528c3d34a997365656f757206fbdf34193e2c3b6f737',
            "Origin": "https://ilambassadorformsprod.azurewebsites.net",
            "Pragma": "no-cache",
            "Referer": "https://ilambassadorformsprod.azurewebsites.net/wastecollectiondays/index",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 OPR/98.0.0.0",
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Chromium";v="112", "Not_A Brand";v="24", "Opera GX";v="98"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

        data_bins = {"bins": []}

        # For each of the months we defined
        for cal_month in months:
            # If we're in Nov/Dec, the calculations won't work since its just adding one, so roll it
            # to next year correctly
            if cal_month == 13:
                cal_month = 1
                cal_year = this_year + 1
            elif cal_month == 14:
                cal_month = 2
                cal_year = this_year + 1
            else:
                cal_year = this_year

            # Data for the calendar
            data = {
                "Month": cal_month,
                "Year": cal_year,
                "Postcode": user_postcode,
                "Uprn": user_uprn,
            }

            # Send it all as a POST
            response = requests.post(
                "https://ilambassadorformsprod.azurewebsites.net/wastecollectiondays/wastecollectioncalendar",
                cookies=cookies,
                headers=headers,
                data=data,
            )

            # If we don't get a HTTP200, throw an error
            if response.status_code != 200:
                raise SystemError(
                    "Error retrieving data! Please try again or raise an issue on GitHub!"
                )

            soup = BeautifulSoup(response.text, features="html.parser")
            soup.prettify()
            # Find all the bits of the current calendar that contain an event
            resultscontainer = soup.find_all("div", {"class": "cal-inner"})

            for result in resultscontainer:
                event = result.find("div", {"class": "events-list"})
                if event:
                    collectiondate = datetime.strptime(
                        result.find("span", class_="day-no")["data-cal-date"],
                        "%Y-%m-%dT%H:%M:%S",
                    ).strftime(date_format)
                    collection_type = result.select_one(
                        ".rc-event-container span"
                    ).text.strip()

                    collection_types = collection_type.split(" and ")

                    for type in collection_types:

                        dict_data = {
                            "type": type,
                            "collectionDate": collectiondate,
                        }
                        data_bins["bins"].append(dict_data)

        return data_bins
