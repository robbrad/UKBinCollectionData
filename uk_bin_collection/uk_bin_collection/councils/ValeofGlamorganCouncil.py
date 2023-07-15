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
        requests.packages.urllib3.disable_warnings()
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-GB,en;q=0.6",
            "Connection": "keep-alive",
            "Referer": "https://www.valeofglamorgan.gov.uk/",
            "Sec-Fetch-Dest": "script",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-site",
            "Sec-GPC": "1",
            "sec-ch-ua": '"Not?A_Brand";v="8", "Chromium";v="108", "Brave";v="108"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        params = {
            "RequestType": "LocalInfo",
            "ms": "ValeOfGlamorgan/AllMaps",
            "group": "Community and Living|Refuse HIDE2",
            "type": "json",
            "callback": "AddressInfoCallback",
            "uid": user_uprn,
            "import": "jQuery35108514154283927682_1673022974838",
            "_": "1673022974840",
        }

        # Get a response from the council
        response = requests.get(
            "https://myvale.valeofglamorgan.gov.uk/getdata.aspx",
            params=params,
            headers=headers,
        ).text

        # Load the JSON and seek out the bin week text, then add it to the calendar URL. Also take the weekly
        # collection type and generate dates for it. Then make a GET request for the calendar
        bin_week = str(
            json.loads(response)["Results"]["Refuse_HIDE2"]["Your_Refuse_round_is"]
        ).replace(" ", "-")
        weekly_collection = str(
            json.loads(response)["Results"]["Refuse_HIDE2"]["Recycling__type"]
        ).capitalize()
        weekly_dates = get_weekday_dates_in_period(
            datetime.now(), days_of_week.get(bin_week.split("-")[0].strip()), amount=48
        )
        schedule_url = f"https://www.valeofglamorgan.gov.uk/en/living/Recycling-and-Waste/collections/{bin_week}.aspx"
        response = requests.get(schedule_url, verify=False)

        # BS4 parses the calendar
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        # Some scraper variables
        collections = []

        # Get the calendar table and find the headers
        table = soup.find("table", {"class": "TableStyle_Activities"}).find("tbody")
        table_headers = table.find("tr").find_all("th")
        # For all rows below the header, find all details in th next row
        for tr in soup.find_all("tr")[1:]:
            row = tr.find_all("td")
            # Parse month and year - month needs converting from text to number
            month_and_year = row[0].text.split()
            if month_and_year[0] in list(calendar.month_abbr):
                collection_month = datetime.strptime(month_and_year[0], "%b").month
            elif month_and_year[0] == "Sept":
                collection_month = int(9)
            else:
                collection_month = datetime.strptime(month_and_year[0], "%B").month
            collection_year = datetime.strptime(month_and_year[1], "%Y").year

            # Get the collection dates column, remove anything that's not a number or space and then convert to dates
            for day in remove_alpha_characters(row[1].text.strip()).split():
                try:
                    bin_date = datetime(collection_year, collection_month, int(day))
                    collections.append((table_headers[1].text.strip().replace(" collection date", ""), bin_date))
                except Exception as ex:
                    continue

        # Add in weekly dates to the tuple
        for date in weekly_dates:
            collections.append(
                (weekly_collection, datetime.strptime(date, date_format))
            )

        # Order all the data, only including future dates
        ordered_data = sorted(collections, key=lambda x: x[1])
        data = {"bins": []}
        for item in ordered_data:
            collection_date = item[1]
            if collection_date.date() >= datetime.now().date():
                dict_data = {
                    "type": item[0],
                    "collectionDate": collection_date.strftime(date_format),
                }
                data["bins"].append(dict_data)

        return data
