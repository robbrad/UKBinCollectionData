from uk_bin_collection.uk_bin_collection.councils.SloughBoroughCouncil import (
    CouncilClass as PublicDashboardCouncil,
)


class CouncilClass(PublicDashboardCouncil):
    """
    Portsmouth retired its AchieveForms lookup in favour of a "Public
    Dashboard" collection calendar on the same platform as Slough's.
    """

    BASE_URL = "https://recyclingandrubbish.portsmouth.gov.uk/PublicDashboard"
