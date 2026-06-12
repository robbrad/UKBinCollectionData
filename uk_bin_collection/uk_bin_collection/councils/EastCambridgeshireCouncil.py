from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)
        
        HOSTNAME = "eastcambs-self.achieveservice.com"
        API_URL = f"https://{HOSTNAME}/apibroker/runLookup"
        INITIAL_URL = f"https://{HOSTNAME}/AchieveForms/"
        COLLECTIONS_LOOKUP_ID = "6784e74793b68" # this is the integration id in json
        PROCESS_ID = "2c7575a6-0139-4555-9d8a-ab504a44d989"
        STAGE_ID = "94ee5097-94db-474d-bc7a-d1796e3ab83a"
        AUTH_LOOKUP_ID = "69d8f92eea3cf"
        
        # set date ranges
        today = datetime.today().date()
        start_date = today
        end_date = today + timedelta(days=42) # The default query on the council website gives 6 weeks

        requests.packages.urllib3.disable_warnings()
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        # Three-step flow
        # Step 1 - Session priming
        r = s.get(INITIAL_URL,
            params={
                "mode": "fill",
                "consentMessage": "yes",
                "form_uri": f"sandbox-publish://AF-Process-{PROCESS_ID}/AF-Stage-{STAGE_ID}/definition.json",
                "process": "1",
                "process_uri": f"sandbox-processes://AF-Process-{PROCESS_ID}",
                "process_id": f"AF-Process-{PROCESS_ID}",
            },
            timeout=30,
            )
        sid_match = re.search(r'"auth-session":"([^"]+)"', r.text)
        sid = sid_match.group(1)
        
        # Step 2 - auth
        r_auth = s.post(
            API_URL,
            params={
                "id": AUTH_LOOKUP_ID,
                "repeat_against": "",
                "noRetry": "false",
                "getOnlyTokens": "undefined",
                "log_id": "",
                "app_name": "AchieveForms",
                "sid": sid,
            },
            json={"formValues": {"Section 1": {}}},
            timeout=30,
        )
        r_auth.raise_for_status()
        auth_data = r_auth.json()
        auth_token = (
            auth_data.get("integration", {})
            .get("transformed", {})
            .get("rows_data", {})
            .get("0", {})
            .get("AuthenticateResponse", "")
        )
        
        # Step 3 - lookup collections
        r_col = s.post(
            API_URL,
            params={
                "id": COLLECTIONS_LOOKUP_ID,
                "repeat_against": "",
                "noRetry": "false",
                "getOnlyTokens": "undefined",
                "log_id": "",
                "app_name": "AchieveForms",
                "sid": sid,
            },
            json={
                "formValues": {
                    "Section 1": {
                        "AuthenticateResponse": {"value": auth_token},
                        "selected_uprn": {"value": uprn},
                        "MinimumDateForNextDates": {
                            "value": start_date.strftime("%Y-%m-%d")
                        },
                        "MaximumDateFormattedNext": {
                            "value": end_date.strftime("%Y-%m-%d")
                        },
                    }
                }
            },
            timeout=30,
        )
        
        col_data = r_col.json()
        soup = BeautifulSoup(col_data['data'], features="xml")
        # Although the data also comes in JSON it is potentially harder to process
        # as the bin type and date are combined together
        # The XML does not have this problem.
        data = {"bins": []}
        for bins in soup.find_all("Row"):
            entries = bins.find_all()
            if len(entries) < 3:
                continue
            _, bin_type, date = entries[:3]
            # The first entry, which we discard, has a concatenation of the bin_type and date
            
            bin_type = bin_type.text
            if not bin_type or not date.text:
                continue
            date = datetime.strptime(date.text, "%d/%m/%Y").date()
            data["bins"].append(
                {"type": bin_type, "collectionDate": date.strftime(date_format)}
            )
        
        return data
