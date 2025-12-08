from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        postcode = kwargs.get("postcode")
        check_uprn(uprn)
        check_postcode(postcode)
        
        api_url = f"https://www.islington.gov.uk/your-area?Postcode={postcode}&Uprn={uprn}"
        
        # Use headers to avoid 403 error
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(api_url, headers=headers)

        soup = BeautifulSoup(response.text, features="html.parser")

        data = {"bins": []}

        # Find the waste and recycling section with proper null checking
        waste_section = soup.find(string="Waste and recycling collections")
        
        if waste_section:
            toggle_content = waste_section.find_next("div", class_="m-toggle-content")
            if toggle_content:
                # New format uses list items instead of table
                waste_list = toggle_content.find("ul")
                if waste_list:
                    list_items = waste_list.find_all("li")
                    for item in list_items:
                        # Parse text like: "Mixed dry recycling - recycling wheelie bin, collected every week on Wednesday"
                        item_text = item.text.strip()
                        if " - " in item_text and "collected" in item_text.lower():
                            # Split on " - " to separate bin type from collection info
                            parts = item_text.split(" - ", 1)
                            bin_type = parts[0].strip()
                            
                            # Extract collection day from the text
                            collection_info = parts[1].lower()
                            
                            # Try to find day of week and calculate next occurrence
                            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                            collection_day_name = None
                            for day in days:
                                if day in collection_info:
                                    collection_day_name = day
                                    break
                            
                            if collection_day_name:
                                # Calculate next occurrence of this day
                                from datetime import datetime, timedelta
                                
                                today = datetime.now()
                                target_day = days.index(collection_day_name)
                                current_day = today.weekday()
                                
                                # Calculate days until next occurrence
                                days_ahead = target_day - current_day
                                if days_ahead <= 0:  # Target day already happened this week
                                    days_ahead += 7
                                
                                next_collection = today + timedelta(days=days_ahead)
                                
                                data["bins"].append(
                                    {
                                        "type": bin_type,
                                        "collectionDate": next_collection.strftime(date_format),
                                    }
                                )

        return data
