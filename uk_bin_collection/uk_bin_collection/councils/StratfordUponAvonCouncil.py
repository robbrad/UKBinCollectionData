from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Get postcode and UPRN from kwargs
        # user_postcode = kwargs.get("postcode")
        user_uprn = kwargs.get("uprn")
        # check_postcode(user_postcode)
        check_uprn(user_uprn)
        url = "https://www.stratford.gov.uk/waste-recycling/when-we-collect.cfm/part/calendar"
        payload = {
            "frmAddress1": "",
            "frmAddress2": "",
            "frmAddress3": "",
            "frmAddress4": "",
            "frmPostcode": "",
            "frmUPRN": user_uprn,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        requests.packages.urllib3.disable_warnings()
        response = requests.request("POST", url, data=payload, headers=headers)

        # Make a BS4 object
        soup = BeautifulSoup(response.content, features="html.parser")
        soup.prettify()

        # Find the table
        table = soup.find("table", class_="table")

        data = {"bins": []}

        if table:
            # Extract the column headers (bin names)
            column_headers = [
                header.text.strip()
                for header in table.select("thead th.text-center strong")
            ]

            # Extract the rows containing collection information
            collection_rows = table.select("tbody tr")

            # Create a dictionary to store the next date for each bin
            next_collection_dates = {bin: None for bin in column_headers}

            # Iterate through the rows
            for row in collection_rows:
                # Get the date from the first cell
                date_str = row.find("td").text.strip()
                date_obj = datetime.strptime(date_str, "%A, %d/%m/%Y")

                # Get the collection information for each bin (td elements with title attribute)
                collection_info = [
                    cell["title"] if cell["title"] else "Not Collected"
                    for cell in row.select("td.text-center")
                ]

                # Iterate through each bin type and its collection date
                for bin, status in zip(column_headers, collection_info):
                    # If the bin hasn't had a collection date yet or the new date is earlier, update it
                    if status != "Not Collected" and (
                        not next_collection_dates[bin]
                        or date_obj < next_collection_dates[bin]
                    ):
                        next_collection_dates[bin] = date_obj

            data["bins"] = [
                {"type": bin, "collectionDate": next_date.strftime(date_format)}
                for bin, next_date in next_collection_dates.items()
            ]
        else:
            print("Table not found in the HTML content.")

        return data
