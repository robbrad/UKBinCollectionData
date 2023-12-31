from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

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
        # Make a BS4 object
        uprn = kwargs.get("uprn")
        usrn = kwargs.get("paon")
        check_uprn(uprn)
        check_usrn(usrn)

        day = datetime.now().date().strftime("%d")
        month = datetime.now().date().strftime("%m")
        year = datetime.now().date().strftime("%Y")

        api_url = (
            f"https://my.crawley.gov.uk/appshost/firmstep/self/apps/custompage/waste?language=en&uprn={uprn}"
            f"&usrn={usrn}&day={day}&month={month}&year={year}"
        )
        response = requests.get(api_url)

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        titles = [title.text for title in soup.select(".title")]
        collection_tag = soup.body.find_all(
            "div", {"class": "col-md-6 col-sm-6 col-xs-6"}, string="Next collection"
        )
        bin_index = 0
        for tag in collection_tag:
            for item in tag.next_elements:
                if (
                    str(item).startswith('<div class="date text-right text-grey">')
                    and str(item) != ""
                ):
                    collection_date = datetime.strptime(item.text, "%A %d %B")
                    next_collection = collection_date.replace(year=datetime.now().year)
                    if datetime.now().month == 12 and next_collection.month == 1:
                        next_collection = next_collection + relativedelta(years=1)

                    dict_data = {
                        "type": titles[bin_index].strip(),
                        "collectionDate": next_collection.strftime(date_format),
                    }
                    data["bins"].append(dict_data)
                    bin_index += 1
                    break
        return data
