import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse

from uk_bin_collection.uk_bin_collection.common import (
    check_postcode,
    check_uprn,
    datetime,
    get_dates_every_x_days,
    json,
    timedelta,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs: str) -> dict[str, list[dict[str, str]]]:
        if (postcode := kwargs.get("postcode")) is None:
            raise KeyError("Missing: postcode")
        if (uprn := kwargs.get("uprn")) is None:
            raise KeyError("Missing: uprn")
        check_postcode(postcode)
        check_uprn(uprn)
        bindata: dict[str, list[dict[str, str]]] = {"bins": []}
        location_x: int = 0
        location_y: int = 0
        location_usrn: str = ""

        # Ensure any cookies set are maintained in a requests session
        s = requests.session()

        # Ask for a new SessionId from the server
        session_id_url = (
            "https://maps.cheltenham.gov.uk/map/Aurora.svc/"
            "RequestSession?userName=guest+CBC&password=&"
            "script=%5CAurora%5CCBC+Waste+Streets.AuroraScript%24"
        )
        session_id_response = s.get(session_id_url)
        session_id_response.raise_for_status()
        session_id = session_id_response.json().get("Session").get("SessionId")

        # Ask what tasks we can do within the session
        tasks_url = (
            f"https://maps.cheltenham.gov.uk/map/Aurora.svc/"
            f"GetWorkflow?sessionId={session_id}&workflowId=wastestreet"
        )
        tasks_response = s.get(tasks_url)
        tasks_response.raise_for_status()
        # JSON response contained a BOM marker
        tasks = json.loads(tasks_response.text[1:])
        retrieve_results_task_id, initialise_map_task_id, drilldown_task_id = (
            None,
            None,
            None,
        )
        # Pull out the ID's of the tasks we will need
        for task in tasks.get("Tasks"):
            if task.get("$type") == "StatMap.Aurora.FetchResultSetTask, StatMapService":
                retrieve_results_task_id = task.get("Id")
            elif task.get("$type") == "StatMap.Aurora.SaveStateTask, StatMapService":
                initialise_map_task_id = task.get("Id")
            elif task.get("$type") == "StatMap.Aurora.DrillDownTask, StatMapService":
                drilldown_task_id = task.get("Id")
        if not all(
            [retrieve_results_task_id, initialise_map_task_id, drilldown_task_id]
        ):
            raise ValueError("Not all task ID's found")

        # Find the X / Y coordinates for the requested postcode
        postcode_search_url = (
            "https://maps.cheltenham.gov.uk/map/Aurora.svc/FindLocation?"
            f"sessionId={session_id}&address={postcode}&limit=1000"
        )
        postcode_search_response = s.get(postcode_search_url)
        postcode_search_response.raise_for_status()
        if len(locations_list := postcode_search_response.json().get("Locations")) == 0:
            raise ValueError("Address locations empty")
        for location in locations_list:
            location_search_url = (
                "https://maps.cheltenham.gov.uk/map/Aurora.svc/FindLocation?"
                f"sessionId={session_id}&locationId={location.get('Id')}"
            )
            location_search_response = s.get(location_search_url)
            location_search_response.raise_for_status()
            if not (location_list := location_search_response.json().get("Locations")):
                raise KeyError("Locations wasn't present in results")
            if not (location_detail := location_list[0].get("Details")):
                raise KeyError("Details wasn't present in location")
            location_uprn = [
                detail.get("Value")
                for detail in location_detail
                if detail.get("Name") == "UPRN"
            ][0]
            if str(location_uprn) == uprn:
                location_usrn = str(
                    [
                        detail.get("Value")
                        for detail in location_detail
                        if detail.get("Name") == "USRN"
                    ][0]
                )
                location_x = location_list[0].get("X")
                location_y = location_list[0].get("Y")
                break

        # Needed to initialise the server to allow follow on call
        open_map_url = (
            "https://maps.cheltenham.gov.uk/map/Aurora.svc/OpenScriptMap?"
            f"sessionId={session_id}"
        )
        if res := s.get(open_map_url):
            res.raise_for_status()

        # Needed to initialise the server to allow follow on call
        save_state_map_url = (
            "https://maps.cheltenham.gov.uk/map/Aurora.svc/ExecuteTaskJob?"
            f"sessionId={session_id}&taskId={initialise_map_task_id}&job="
            "%7BTask%3A+%7B+%24type%3A+%27StatMap.Aurora.SaveStateTask%2C"
            "+StatMapService%27+%7D%7D"
        )
        if res := s.get(save_state_map_url):
            res.raise_for_status()

        # Start search for address given by x / y coord
        drilldown_map_url = (
            "https://maps.cheltenham.gov.uk/map/Aurora.svc/ExecuteTaskJob?"
            f"sessionId={session_id}&taskId={drilldown_task_id}&job=%7B%22"
            f"QueryX%22%3A{location_x}%2C%22QueryY%22%3A{location_y}%2C%22"
            "Task%22%3A%7B%22Type%22%3A%22StatMap.Aurora.DrillDownTask%2C"
            "+StatMapService%22%7D%7D"
        )
        if res := s.get(drilldown_map_url):
            res.raise_for_status()

        # Get results from search for address given by x / y coord
        address_details_url = (
            "https://maps.cheltenham.gov.uk/map/Aurora.svc/ExecuteTaskJob?"
            f"sessionId={session_id}&taskId={retrieve_results_task_id}"
            f"&job=%7B%22QueryX%22%3A{location_x}%2C%22QueryY%22%3A"
            f"{location_y}%2C%22Task%22%3A%7B%22Type%22%3A%22"
            "StatMap.Aurora.FetchResultSetTask%2C+StatMapService"
            "%22%2C%22ResultSetName%22%3A%22inspection%22%7D%7D"
        )
        address_details_response = s.get(address_details_url)
        address_details_response.raise_for_status()
        # JSON response contained a BOM marker, skip first character
        address_details = json.loads(address_details_response.text[1:])
        if not (task_results := address_details.get("TaskResult")):
            raise KeyError("TaskResult wasn't present in results")
        if not (distance_export_set := task_results.get("DistanceOrderedSet")):
            raise KeyError("DistanceOrderedSet wasn't present in TaskResult")
        if not (result_set := distance_export_set.get("ResultSet")):
            raise KeyError("ResultSet wasn't present in DistanceOrderedSet")
        if not (result_tables := result_set.get("Tables")):
            raise KeyError("Tables wasn't present in ResultSet")
        result = result_tables[0]
        column_names: dict[int, str] = {}
        result_dict: dict[str, str | int] = {}
        for column in result.get("ColumnDefinitions"):
            column_names[column.get("ColumnIndex")] = column.get("ColumnName")
        for r in result.get("Records"):
            result_dict: dict[str, str | int] = {}
            for idx, column_value in enumerate(r):
                if not (column_name := column_names.get(idx)):
                    raise IndexError("Column index out of range")
                result_dict[column_name.upper()] = column_value
            # Validate the street against the USRN. Some locations can return multiple results.
            # Break on first match of USRN
            # TODO: Need to select the correct option out of all available options
            if location_usrn == str(result_dict.get("USRN")):
                break

        refuse_week, recycling_week, garden_week = 0, 0, 0
        # After we've got the correct result, pull out the week number each bin type is taken on
        if (refuse_week_raw := result_dict.get("New_Refuse_Week".upper())) is not None:
            refuse_week = int(refuse_week_raw)
        if (
            recycling_week_raw := result_dict.get("New_Recycling_Week".upper())
        ) is not None:
            recycling_week = int(recycling_week_raw)
        if (garden_week_raw := result_dict.get("Garden_Bin_Week".upper())) is not None:
            garden_week = int(garden_week_raw)

        if not all([refuse_week, recycling_week, garden_week]):
            raise KeyError("Not all week numbers found")

        days_of_week = [
            "MON",
            "TUE",
            "WED",
            "THU",
            "FRI",
            "SAT",
            "SUN",
        ]

        refuse_day_offset = days_of_week.index(
            str(result_dict.get("New_Refuse_Day_internal".upper())).upper()
        )
        recycling_day_offset = days_of_week.index(
            str(result_dict.get("New_Recycling_Day".upper())).upper()
        )
        garden_day_offset = days_of_week.index(
            str(result_dict.get("New_Garden_Day".upper())).upper()
        )
        food_day_offset = days_of_week.index(
            str(result_dict.get("New_Food_Day".upper())).upper()
        )

        # Initialise WEEK-1/WEEK-2 based on known details
        week_1_epoch = datetime(2025, 1, 13)

        # Start of this week
        this_week = datetime.now() - timedelta(days=datetime.now().weekday())

        # If there's an even number of weeks between the week-1
        # epoch and this week, then this week is of type week-1
        if (((this_week - week_1_epoch).days // 7)) % 2 == 0:
            week = {1: this_week, 2: this_week + timedelta(days=7)}
        else:
            week = {1: this_week - timedelta(days=7), 2: this_week}

        refuse_dates: list[str] = get_dates_every_x_days(week[refuse_week], 14, 28)
        recycling_dates: list[str] = get_dates_every_x_days(
            week[recycling_week], 14, 28
        )
        garden_dates: list[str] = get_dates_every_x_days(week[garden_week], 14, 28)

        # Build a dictionary of bank holiday changes
        bank_holiday_bins_url = "https://www.cheltenham.gov.uk/bank-holiday-collections"
        response = requests.get(bank_holiday_bins_url)
        soup = BeautifulSoup(response.content, "html.parser")
        response.close()
        tables = soup.find_all("table")

        # Build a dictionary to modify any bank holiday collections
        bh_dict = {}
        for table in tables:
            # extract table body
            for row in table.find_all("tr")[1:]:
                if row.find_all("td")[1].text.strip() == "Normal collection day":
                    bh_dict[
                        parse(
                            row.find_all("td")[0].text.strip(),
                            dayfirst=True,
                            fuzzy=True,
                        ).date()
                    ] = parse(
                        row.find_all("td")[0].text.strip(), dayfirst=True, fuzzy=True
                    ).date()
                else:
                    bh_dict[
                        parse(
                            row.find_all("td")[0].text.strip(),
                            dayfirst=True,
                            fuzzy=True,
                        ).date()
                    ] = parse(
                        row.find_all("td")[1].text.strip(), dayfirst=True, fuzzy=True
                    ).date()

        for refuse_date in refuse_dates:
            collection_date = datetime.strptime(refuse_date, "%d/%m/%Y") + timedelta(
                days=refuse_day_offset
            )
            if collection_date in bh_dict:
                collection_date = bh_dict[collection_date]
            collection_date = collection_date.strftime("%d/%m/%Y")

            dict_data = {
                "type": "Refuse Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        for recycling_date in recycling_dates:

            collection_date = datetime.strptime(recycling_date, "%d/%m/%Y") + timedelta(
                days=recycling_day_offset
            )
            if collection_date in bh_dict:
                collection_date = bh_dict[collection_date]
            collection_date = collection_date.strftime("%d/%m/%Y")

            dict_data = {
                "type": "Recycling Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        for garden_date in garden_dates:

            collection_date = datetime.strptime(garden_date, "%d/%m/%Y") + timedelta(
                days=garden_day_offset
            )
            if collection_date in bh_dict:
                collection_date = bh_dict[collection_date]
            collection_date = collection_date.strftime("%d/%m/%Y")

            dict_data = {
                "type": "Garden Waste Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        if (
            food_waste_week := str(
                result_dict.get("FOOD_WASTE_WEEK_EXTERNAL", "")
            ).upper()
        ) == "weekly".upper():
            food_dates: list[str] = get_dates_every_x_days(week[1], 7, 56)

            for food_date in food_dates:

                collection_date = datetime.strptime(food_date, "%d/%m/%Y") + timedelta(
                    days=food_day_offset
                )
                if collection_date in bh_dict:
                    collection_date = bh_dict[collection_date]
                collection_date = collection_date.strftime("%d/%m/%Y")

                dict_data = {
                    "type": "Food Waste Bin",
                    "collectionDate": collection_date,
                }
                bindata["bins"].append(dict_data)
        # Sometimes the food bin is collected on different days between
        # week-1 and week-2
        else:
            first_week: str | int
            second_week_detail: str
            first_week, _, second_week_detail = food_waste_week.partition("&")
            first_week = int(first_week.strip())

            second_week_day, _, second_week_number = second_week_detail.partition(
                "WEEK"
            )
            second_week_number = int(second_week_number.strip())
            second_week_day: str = second_week_day.strip()[:3]

            food_dates_first: list[str] = get_dates_every_x_days(
                week[first_week], 14, 28
            )
            food_dates_second: list[str] = get_dates_every_x_days(
                week[second_week_number], 14, 28
            )
            second_week_offset = days_of_week.index(second_week_day)

            for food_date in food_dates_first:

                collection_date = datetime.strptime(food_date, "%d/%m/%Y") + timedelta(
                    days=food_day_offset
                )
                if collection_date in bh_dict:
                    collection_date = bh_dict[collection_date]
                collection_date = collection_date.strftime("%d/%m/%Y")

                dict_data = {
                    "type": "Food Waste Bin",
                    "collectionDate": collection_date,
                }
                bindata["bins"].append(dict_data)
            for food_date in food_dates_second:

                collection_date = datetime.strptime(food_date, "%d/%m/%Y") + timedelta(
                    days=second_week_offset
                )
                if collection_date in bh_dict:
                    collection_date = bh_dict[collection_date]
                collection_date = collection_date.strftime("%d/%m/%Y")

                dict_data = {
                    "type": "Food Waste Bin",
                    "collectionDate": collection_date,
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate", ""), "%d/%m/%Y")
        )
        return bindata
