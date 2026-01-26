import re
from datetime import datetime

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        try:
            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)

            data = {"bins": []}

            import requests

            url = "https://bolton.portal.uk.empro.verintcloudservices.com/site/empro-bolton/request/es_bin_collection_dates"

            session = requests.Session()

            # Equivalent to: $session.UserAgent = "..."
            session.headers.update(
                {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/143.0.0.0 Safari/537.36"
                    )
                }
            )

            headers = {
                "Referer": "https://www.bolton.gov.uk/",
            }

            resp = session.get(url, headers=headers, timeout=30)
            resp.raise_for_status()

            # Equivalent to $response1.Content
            soup = BeautifulSoup(resp.text, features="html.parser")
            soup.prettify()

            tag = soup.find("meta", attrs={"name": "_csrf_token"})
            csrf_token = tag.get("content") if tag else None
            # print(csrf_token)

            url = "https://bolton.form.uk.empro.verintcloudservices.com/api/citizen?archived=Y&preview=false&locale=en"
            headers = {
                "Referer": "https://bolton.portal.uk.empro.verintcloudservices.com/",
            }
            resp = session.get(url, headers=headers, timeout=30)
            resp.raise_for_status()

            authorization = resp.headers["authorization"]
            # print(authorization)

            url = "https://bolton.form.uk.empro.verintcloudservices.com/api/custom?action=es_get_bin_collection_dates&actionedby=uprn_changed&loadform=true&access=citizen&locale=en"

            headers = {
                "Authorization": authorization,
                "Referer": "https://bolton.portal.uk.empro.verintcloudservices.com/",
                "X-CSRF-TOKEN": csrf_token,
            }

            today = datetime.today()
            two_months = datetime.today() + relativedelta(months=2)
            payload = {
                "name": "es_bin_collection_dates",
                "data": {
                    "uprn": user_uprn,
                    "start_date": today.strftime("%d/%m/%Y"),
                    "end_date": two_months.strftime("%d/%m/%Y"),
                },
            }

            resp = session.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()

            json = resp.json()  # or json.loads(your_text)

            html = json["data"]["collection_dates"]
            soup = BeautifulSoup(html, "html.parser")

            # Each bin block is a <div style="overflow:auto; margin-bottom:30px;">
            for block in soup.find_all("div", style=re.compile(r"overflow:auto")):
                title_tag = block.find("strong")
                if not title_tag:
                    continue

                bin_name = " ".join(title_tag.get_text(" ", strip=True).split()).rstrip(
                    ":"
                )
                dates = [li.get_text(" ", strip=True) for li in block.find_all("li")]

                if dates:
                    for date in dates:
                        dict_data = {
                            "type": bin_name.strip(),
                            "collectionDate": (
                                datetime.strptime(date, "%A %d %B %Y")
                            ).strftime(date_format),
                        }
                        data["bins"].append(dict_data)

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise

        return data
