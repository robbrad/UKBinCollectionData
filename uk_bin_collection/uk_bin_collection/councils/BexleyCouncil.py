from uk_bin_collection.uk_bin_collection.councils.SocietyWorks import SocietyWorksClass


class CouncilClass(SocietyWorksClass):
    """
    Bexley specific CouncilClass
    """
    BASE_URL = "https://waste.bexley.gov.uk/"

    def _uprn_to_property_id(self, uprn):
        """Bexley use the UPRN as the identifier"""
        return uprn
