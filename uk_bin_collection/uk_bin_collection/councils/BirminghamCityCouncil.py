from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def get_token(page) -> str:
    """
    Get a __token to include in the form data
        :param page: Page html
        :return: Form __token
    """
    soup = BeautifulSoup(page.text, features="html.parser")
    soup.prettify()
    token = soup.find("input", {"name": "__token"}).get("value")
    return token


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def get_data(self, url) -> str:
        """This method makes the request to the council

        Keyword arguments:
        url -- the url to get the data from
        """
        # Set a user agent so we look like a browser ;-)
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/108.0.0.0 Safari/537.36"
        )
        headers = {"User-Agent": user_agent}
        requests.packages.urllib3.disable_warnings()

        # Make the Request - change the URL - find out your property number
        try:
            session = requests.Session()
            session.headers.update(headers)
            full_page = session.get(url)
            return full_page
        except requests.exceptions.HTTPError as errh:
            _LOGGER.error(f"Http Error: {errh}")
            raise
        except requests.exceptions.ConnectionError as errc:
            _LOGGER.error(f"Error Connecting: {errc}")
            raise
        except requests.exceptions.Timeout as errt:
            _LOGGER.error(f"Timeout Error: {errt}")
            raise
        except requests.exceptions.RequestException as err:
            _LOGGER.error(f"Oops: Something Else {err}")
            raise

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        postcode = kwargs.get("postcode")
        check_uprn(uprn)
        check_postcode(postcode)

        values = {
            "__token": get_token(page),
            "page": "491",
            "locale": "en_GB",
            "q1f8ccce1d1e2f58649b4069712be6879a839233f_0_0": postcode,
            "q1f8ccce1d1e2f58649b4069712be6879a839233f_1_0": uprn,
            "next": "Next",
        }
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}
        requests.packages.urllib3.disable_warnings()
        response = requests.request(
            "POST",
            "https://www.birmingham.gov.uk/xfp/form/619",
            headers=headers,
            data=values,
        )

        soup = BeautifulSoup(response.text, features="html.parser")

        rows = soup.find("table").find_all("tr")

        # Form a JSON wrapper
        data = {"bins": []}

        # Loops the Rows
        for row in rows:
            cells = row.find_all("td")
            if cells:
                bin_type = cells[0].get_text(strip=True)
                collection_next = cells[1].get_text(strip=True)

                collection_date = re.findall("\(.*?\)", collection_next)

                if len(collection_date) != 1:
                    continue

                collection_date_obj = parse(re.sub("[()]", "", collection_date[0])).date()

                # since we only have the next collection day, if the parsed date is in the past,
                # assume the day is instead next month
                if collection_date_obj < datetime.now().date():
                    collection_date_obj += relativedelta(months=1)

                # Make each Bin element in the JSON
                dict_data = {
                    "type": bin_type,
                    "collectionDate": collection_date_obj.strftime(date_format),
                }

                # Add data to the main JSON Wrapper
                data["bins"].append(dict_data)

        return data
