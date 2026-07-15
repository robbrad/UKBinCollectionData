from uk_bin_collection.uk_bin_collection.councils.LondonBoroughEaling import (
    CouncilClass as LondonBoroughEalingCouncilClass,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Deprecated duplicate of LondonBoroughEaling - both targeted the same
    Ealing Council API (#1884). Kept as a thin alias so existing users'
    saved config entries referencing "EalingCouncil" keep working; new
    setups should use LondonBoroughEaling.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        return LondonBoroughEalingCouncilClass().parse_data(page, **kwargs)
