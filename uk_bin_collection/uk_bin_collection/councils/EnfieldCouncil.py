from datetime import datetime
import curl_cffi #better impersonation than manual headers

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        r = curl_cffi.requests.get(
           f"https://www.enfield.gov.uk/_design/integrations/bartec/find-my-collection/rest/schedule?uprn={uprn}",
            headers={
                "Accept": "*/*",
                "Referer": "https://www.enfield.gov.uk/services/rubbish-and-recycling/find-my-collection-day",
                "Connection": "keep-alive",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            },
            impersonate="firefox",
            timeout=30
        )
        
        r.raise_for_status()

        text = r.text.lstrip()
        if text.startswith("<!DOCTYPE html"):
            raise RuntimeError("Cloudflare HTML returned instead of JSON")

        data = r.json()

        bindata = {"bins": []}

        for item in data:
            job_name = (
                item.get("JobName", {}).get("_text")
                or item.get("Description", {}).get("_text")
            )
            scheduled = item.get("ScheduledStart", {}).get("_text")

            if not job_name or not scheduled:
                continue

            dt = datetime.fromisoformat(scheduled)
            collection_date = dt.strftime(date_format)
            contains_date(collection_date)

            bindata["bins"].append(
                {
                    "type": job_name,
                    "collectionDate": collection_date,
                }
            )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], "%d/%m/%Y")
        )

        return bindata
