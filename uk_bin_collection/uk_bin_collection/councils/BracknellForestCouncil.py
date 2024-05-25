import time

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def get_headers(base_url: str, method: str) -> dict[str, str]:
    """
    Gets request headers
        :rtype: dict[str, str]
        :param base_url: Base URL to use
        :param method: Method to use
        :return: Request headers
    """
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Host": "selfservice.mybfc.bracknell-forest.gov.uk",
        "Origin": base_url,
        "sec-ch-ua": '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "Windows",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-User": "?1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/109.0.0.0 Safari/537.36",
    }
    if method.lower() == "post":
        headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["Sec-Fetch-Mode"] = "cors"
        headers["Sec-Fetch-Mode"] = "same-origin"
        headers["X-Requested-With"] = "XMLHttpRequest"
    else:
        headers["Accept"] = (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;"
            "q=0.8,application/signed-exchange;v=b3;q=0.9"
        )
        headers["Sec-Fetch-Mode"] = "navigate"
        headers["Sec-Fetch-Mode"] = "none"
    return headers


def get_session_storage_global() -> object:
    """
    Gets session storage global object
        :rtype: object
        :return: Session storage global object
    """
    return {
        "destination_stack": [
            "w/webpage/waste-collection-days",
        ],
        "last_context_record_id": "86086077",
    }


def get_csrf_token(s: requests.session, base_url: str) -> str:
    """
    Gets a CSRF token
        :rtype: str
        :param s: requests.session() to use
        :param base_url: Base URL to use
        :return: CSRF token
    """
    csrf_token = ""
    response = s.get(
        base_url + "/w/webpage/waste-collection-days",
        headers=get_headers(base_url, "GET"),
    )
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()
        app_body = soup.find("div", {"class": "app-body"})
        script = app_body.find("script", {"type": "text/javascript"}).string
        p = re.compile("var CSRF = ('|\")(.*?)('|\");")
        m = p.search(script)
        csrf_token = m.groups()[1]
    else:
        raise ValueError(
            "Code 1: Failed to get a CSRF token. Please ensure the council website is online first,"
            " then open an issue on GitHub."
        )
    return csrf_token


def get_address_id(
    s: requests.session, base_url: str, csrf_token: str, postcode: str, paon: str
) -> str:
    """
    Gets the address ID
        :rtype: str
        :param s: requests.session() to use
        :param base_url: Base URL to use
        :param csrf_token: CSRF token to use
        :param postcode: Postcode to use
        :param paon: House number/address to find
        :return: address ID
    """
    address_id = "0"
    # Get the addresses for the postcode
    form_data = {
        "code_action": "find_addresses",
        "code_params": '{"search":"' + postcode + '"}',
        "_session_storage": json.dumps(
            {
                "/w/webpage/waste-collection-days": {},
                "_global": get_session_storage_global(),
            }
        ),
        "action_cell_id": "PCL0003988FEFFB1",
        "action_page_id": "PAG0000570FEFFB1",
        "form_check_ajax": csrf_token,
    }
    response = s.post(
        base_url
        + "/w/webpage/waste-collection-days?webpage_subpage_id=PAG0000570FEFFB1"
        "&webpage_token=390170046582b0e3d7ca68ef1d6b4829ccff0b1ae9c531047219c6f9b5295738"
        "&widget_action=handle_event",
        headers=get_headers(base_url, "POST"),
        data=form_data,
    )
    if response.status_code == 200:
        json_response = json.loads(response.text)
        addresses = json_response["response"]["addresses"]["items"]
        # Find the matching address id for the paon
        for address in addresses:
            # Check for full matches first
            if address.get("Description") == paon:
                address_id = address.get("Id")
                break
        # Check for matching start if no full match found
        if address_id == "0":
            for address in addresses:
                if address.get("Description").split()[0] == paon.strip():
                    address_id = address.get("Id")
                    break
        # Check match was found
        if address_id == "0":
            raise ValueError(
                "Code 2: No matching address for house number/full address found."
            )
    else:
        raise ValueError("Code 3: No addresses found for provided postcode.")
    return address_id


def get_collection_data(
    s: requests.session, base_url: str, csrf_token: str, address_id: str
) -> str:
    """
    Gets the collection data
        :rtype: str
        :param s: requests.session() to use
        :param base_url: Base URL to use
        :param csrf_token: CSRF token to use
        :param address_id: Address id to use
        :param retries: Retries count
        :return: Collection data
    """
    collection_data = ""
    if address_id != "0":
        form_data = {
            "code_action": "find_rounds",
            "code_params": '{"addressId":"' + address_id + '"}',
            "_session_storage": json.dumps(
                {
                    "/w/webpage/waste-collection-days": {},
                    "_global": get_session_storage_global(),
                }
            ),
            "action_cell_id": "PCL0003988FEFFB1",
            "action_page_id": "PAG0000570FEFFB1",
            "form_check_ajax": csrf_token,
        }
        response = s.post(
            base_url
            + "/w/webpage/waste-collection-days?webpage_subpage_id=PAG0000570FEFFB1"
            "&webpage_token=390170046582b0e3d7ca68ef1d6b4829ccff0b1ae9c531047219c6f9b5295738"
            "&widget_action=handle_event",
            headers=get_headers(base_url, "POST"),
            data=form_data,
        )
        if response.status_code == 200 and len(response.text) > 0:
            json_response = json.loads(response.text)
            collection_data = json_response["response"]["collections"]
        else:
            raise ValueError("Code 4: Failed to get bin data.")
    return collection_data


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        requests.packages.urllib3.disable_warnings()
        s = requests.session()
        base_url = "https://selfservice.mybfc.bracknell-forest.gov.uk"
        paon = kwargs.get("paon")
        postcode = kwargs.get("postcode")
        check_paon(paon)
        check_postcode(postcode)

        # Firstly, get a CSRF (cross-site request forgery) token
        csrf_token = get_csrf_token(s, base_url)
        # Next, get the address_id
        address_id = get_address_id(s, base_url, csrf_token, postcode, paon)
        # Finally, use the address_id to get the collection data
        collection_data = get_collection_data(s, base_url, csrf_token, address_id)
        if collection_data != "":
            # Form a JSON wrapper
            data = {"bins": []}

            for c in collection_data:
                collection_type = c["round"]
                for c_date in c["upcomingCollections"]:
                    collection_date = (
                        re.search(r"Your (.*) is(.*)", c_date).group(2).strip()
                    )
                    dict_data = {
                        "type": collection_type,
                        "collectionDate": datetime.strptime(
                            collection_date, "%A %d %B %Y"
                        ).strftime(date_format),
                    }
                    data["bins"].append(dict_data)

            if len(data["bins"]) == 0:
                raise ValueError(
                    "Code 5: No bin data found. Please ensure the council website is showing data first,"
                    " then open an issue on GitHub."
                )

            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
            )
            return data
