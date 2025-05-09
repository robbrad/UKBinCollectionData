from datetime import datetime

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import (
    date_format,
    get_date_with_ordinal,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        # Handle both string and Response objects
        page_content = page.text if hasattr(page, "text") else page

        soup = BeautifulSoup(page_content, features="html.parser")

        data = {"bins": []}
        collections = []

        # Find all bin collection rows
        bin_rows = soup.find_all("div", class_="bin-collection-listing-row")

        if not bin_rows:
            raise ValueError("No bin collection rows found in HTML")

        for bin_row in bin_rows:
            try:
                # Get bin type from h2
                bin_type_elem = bin_row.find("h2")
                if not bin_type_elem:
                    continue
                bin_type = bin_type_elem.text.strip()

                # Find next collection date - look for all <p> tags
                paragraphs = bin_row.find_all("p")

                for p in paragraphs:
                    if p.get_text() and "Next collection:" in p.get_text():
                        date_str = p.get_text().replace("Next collection:", "").strip()
                        # Extract day number from date string (e.g. "2" from "Friday 2nd May")
                        day_number = int("".join(filter(str.isdigit, date_str)))
                        # Replace ordinal in date string with plain number
                        date_str = date_str.replace(
                            get_date_with_ordinal(day_number), str(day_number)
                        )

                        try:
                            # Parse date with full format
                            bin_date = datetime.strptime(date_str, "%A %d %B")

                            # Add current year since it's not in the date string
                            current_year = datetime.now().year
                            bin_date = bin_date.replace(year=current_year)

                            # If the date is in the past, it's probably for next year
                            if bin_date < datetime.now():
                                bin_date = bin_date.replace(year=current_year + 1)

                            collections.append((bin_type, bin_date))
                            print(
                                f"Successfully parsed date for {bin_type}: {bin_date}"
                            )
                            break

                        except ValueError as e:
                            print(
                                f"Failed to parse date '{date_str}' for {bin_type}: {e}"
                            )
                            continue

            except Exception as e:
                print(f"Error processing bin row: {e}")
                continue

        if not collections:
            raise ValueError("No valid collection dates found")

        ordered_data = sorted(collections, key=lambda x: x[1])
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
