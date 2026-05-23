import json

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Fenland's GIS layer endpoint is behind Cloudflare JS challenge.
    Load the page in Selenium to pass the challenge, then fetch the
    JSON API from within the browser context.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        headless = kwargs.get("headless")
        web_driver = kwargs.get("web_driver")
        user_agent = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        )
        driver = create_webdriver(web_driver, headless, user_agent, __name__)

        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                },
            )

            page_url = "https://www.fenland.gov.uk/article/13114/"
            driver.get(page_url)

            WebDriverWait(driver, 20).until(
                lambda d: d.title != "Just a moment..."
            )

            api_url = (
                f"/article/13114/?type=loadlayer&layerId=2"
                f"&uprn={user_uprn}&lat=0.000000000001&lng=0.000000000001"
            )

            result = driver.execute_async_script(
                """
                var callback = arguments[arguments.length - 1];
                fetch(arguments[0], {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json'
                    }
                })
                .then(r => r.text())
                .then(t => callback(t))
                .catch(e => callback('ERROR: ' + e));
                """,
                api_url,
            )

            if result.startswith("ERROR:"):
                raise ValueError(f"API fetch failed: {result}")

            try:
                data_resp = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                raise ValueError("Invalid response from Fenland API")
            if not data_resp.get("features"):
                raise ValueError("No features found in API response")

            json_data = data_resp["features"][0]["properties"]["upcoming"]
            data = {"bins": []}

            for item in json_data:
                for bin_info in item["collections"]:
                    data["bins"].append(
                        {
                            "type": bin_info["desc"],
                            "collectionDate": datetime.strptime(
                                bin_info["collectionDate"], "%Y-%m-%dT%H:%M:%SZ"
                            ).strftime(date_format),
                        }
                    )

            return data
        finally:
            driver.quit()
