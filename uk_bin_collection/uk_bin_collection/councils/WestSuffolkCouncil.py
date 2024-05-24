import itertools

from bs4 import BeautifulSoup, Tag
from dateutil.parser import parse as date_parse

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}
        user_uprn = kwargs.get("uprn")

        api_url = f"https://maps.westsuffolk.gov.uk/MyWestSuffolk.aspx?action=SetAddress&UniqueId={user_uprn}"

        response = requests.get(api_url)

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        def panel_search(cur_tag: Tag):
            """
            Helper function to find the correct tag
            """
            if cur_tag.name != "div":
                return False

            tag_class = cur_tag.attrs.get("class", None)
            if tag_class is None:
                return False

            parent_has_header = cur_tag.parent.find_all(
                "h4", string="Bin collection days"
            )
            if len(parent_has_header) < 1:
                return False

            return "atPanelData" in tag_class

        collection_tag = soup.body.find_all(panel_search)

        # Parse the resultant div
        for tag in collection_tag:
            text_list = list(tag.stripped_strings)
            # Create and parse the list as tuples of name:date
            for bin_name, collection_date in itertools.batched(text_list, 2):
                try:
                    # Clean-up the bin_name
                    bin_name_clean = (
                        bin_name.strip()
                        .replace("\r", "")
                        .replace("\n", "")
                        .replace(":", "")
                    )
                    bin_name_clean = re.sub(" +", " ", bin_name_clean)

                    # Get the bin colour
                    bin_colour = "".join(re.findall(r"^(.*) ", bin_name_clean))

                    # Parse the date
                    next_collection = date_parse(collection_date)
                    next_collection = next_collection.replace(year=datetime.now().year)

                    dict_data = {
                        "type": bin_name_clean,
                        "colour": bin_colour,
                        "collectionDate": next_collection.strftime(date_format),
                    }

                    data["bins"].append(dict_data)

                except Exception as ex:
                    raise ValueError(f"Error parsing bin data: {ex}")

        return data
