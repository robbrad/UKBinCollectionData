from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        soup = BeautifulSoup(page.text, features="html.parser")
        collections = soup.find_all("h3", {"class": "waste-service-name"})
        for c in collections:
            rows = c.find_next_sibling("div", {"class": "govuk-grid-row"}).find_all(
                "div", {"class": "govuk-summary-list__row"}
            )
            for row in rows:
                if row.find("dt").get_text().strip().lower() == "next collection":
                    collection_date = (
                        remove_ordinal_indicator_from_date_string(row.find("dd").get_text()).strip()
                    )
                    dict_data = {
                        "type": c.get_text().strip().capitalize(),
                        "collectionDate": get_next_occurrence_from_day_month(datetime.strptime(
                            collection_date + " " + datetime.now().strftime("%Y"),
                            "%A, %d %B %Y",
                        )).strftime(date_format),
                    }
                    data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
