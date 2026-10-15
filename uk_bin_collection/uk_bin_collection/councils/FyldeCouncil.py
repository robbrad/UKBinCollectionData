"""FyldeCouncil - retired 2026-10-15.

Fylde Borough Council moved its bin collection lookup behind a user account.
The page this scraper used to parse,
https://fylde.gov.uk/resident/bins-recycling-and-rubbish/bin-collection-day,
now redirects to the "Digital Waste Portal" at
https://new.fylde.gov.uk/wasteportal/, which requires registration - the
portal states that previous login details no longer work and that you must
complete registration before you can see your collections. Verified live from
a UK residential connection on 2026-10-15.

The old scraper read a Bartec `Token` out of an `<iframe id="bartec-iframe">`
on that page and used it to call
https://collectiveview.bartec-systems.com/R152/GetData.ashx. There is no
public iframe and no token any more, so the request can no longer be built.
This is not a selector problem: the data now sits behind credentials this
project cannot hold on a user's behalf.

The module is deliberately kept rather than deleted.
`collect_data.import_council_module` imports the council module by the name
stored verbatim in each Home Assistant user's saved config, so deleting the
file would turn this explainable failure into an ImportError. The
`FyldeCouncil` entry has been removed from
`uk_bin_collection/tests/input.json`, so the council is no longer offered to
new Home Assistant users and is no longer exercised by the live test suite.
"""

from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

RETIREMENT_MESSAGE = (
    "FyldeCouncil was retired on 2026-10-15. Fylde Borough Council now "
    "requires a registered account to see bin collection dates: the old "
    "public bin collection day page redirects to the Digital Waste Portal at "
    "https://new.fylde.gov.uk/wasteportal/, which requires registration, and "
    "previous login details no longer work there. No public endpoint is left "
    "for this integration to read, so no scraper can be provided. Look up "
    "your collections at https://new.fylde.gov.uk/wasteportal/ and remove "
    "FyldeCouncil from your configuration."
)


class CouncilClass(AbstractGetBinDataClass):
    """Retired council. See the module docstring for why."""

    def parse_data(self, page: str, **kwargs) -> dict:
        raise NotImplementedError(RETIREMENT_MESSAGE)
