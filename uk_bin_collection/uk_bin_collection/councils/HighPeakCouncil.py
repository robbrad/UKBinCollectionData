from uk_bin_collection.uk_bin_collection.councils.SloughBoroughCouncil import (
    CouncilClass as PublicDashboardCouncil,
)


class CouncilClass(PublicDashboardCouncil):
    """Public Dashboard collection calendar, on the same platform as Slough's."""

    BASE_URL = "https://bins.highpeak.gov.uk/PublicDashboard"
