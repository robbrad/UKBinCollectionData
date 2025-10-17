import logging
from datetime import datetime
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

logger = logging.getLogger(__name__)


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        # diable warnings so that we can ignore cert verification
        requests.packages.urllib3.disable_warnings()

        # Fetch the schedule page
        response = requests.get(
            f"https://www.northtyneside.gov.uk/waste-collection-schedule/view/{user_uprn}",
            verify=False,
        )


        # Parse form page and get the day of week and week offsets
        soup = BeautifulSoup(response.text, features="html.parser")
        schedule = soup.find("div", {"class": "waste-collection__schedule"})

        if schedule is None:
            raise Exception("No waste-collection schedule info found - has the page changed?")


        # Find days of form:
        #
        # <li class="waste-collection__day">
        #   <span class="waste-collection__day--day"><time datetime="2025-11-13">13</time></span>
        #   <span class="waste-collection__day--type">Recycling</span>
        #   <span class="waste-collection__day--colour waste-collection__day--grey">Grey</span>
        # </li>
        #
        #
        # Note that on back holidays the collection type is of form:
        # ...
        # <span class="waste-collection__day--type">Recycling
        #    <span>
        #      Public holiday - services may be affected. Check service updates on <a href="/household-rubbish-and-recycling/household-bin-collections/bank-holiday-bin-collections">our website</a>
        #    </span>
        # </span>
        # ...

        collections = []

        for day in schedule.find_all("li", {"class": "waste-collection__day"}):
            try:
                # extract the date, bin type and colour
                collection_date = datetime.strptime(day.find("time")["datetime"], "%Y-%m-%d")

                # for the collection type we only want the text before any nested span
                type_span = day.find("span", {"class": "waste-collection__day--type"})
                bin_type = next(type_span.strings).strip()

                bin_colour = day.find("span", {"class": "waste-collection__day--colour"}).text.strip()

                collections.append((f'{bin_type} ({bin_colour})', collection_date))

            except Exception as e:
                # here NoneType typically suggests parsing errors so report them and continue
                if "NoneType" in str(e):
                    logger.warning(f'Error while processing {day}: {e}')
                    continue
                raise

        return {
            "bins": [
                {
                    "type": item[0],
                    "collectionDate": item[1].strftime(date_format),
                }
                for item in sorted(collections, key=lambda x: x[1])
            ]
        }
