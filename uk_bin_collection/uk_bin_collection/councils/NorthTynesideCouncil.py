import math
from datetime import *

import requests
from bs4 import BeautifulSoup
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
        requests.packages.urllib3.disable_warnings()
        data = {"bins": []}
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)

        # Get form data
        s = requests.session()
        cookies = {
            "ntc-cookie-policy": "1",
            "SSESS6ec6d5d2d471c0357053d5993a839bce": "qBdR7XhmSMd5_PDBIqG0It2R0Fq67igrejRY-WOcskE",
            "has_js": "1",
        }
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.7",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Origin": "https://my.northtyneside.gov.uk",
            "Referer": "https://my.northtyneside.gov.uk/category/81/bin-collection-dates",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not?A_Brand";v="8", "Chromium";v="108", "Brave";v="108"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        ajax_data = {
            "postcode": user_postcode,
            "form_build_id": "form-BQ47tM0NKADE0s8toYkdSef3QBn6lDM-yBseqIOho80",
            "form_id": "ntc_address_wizard",
            "_triggering_element_name": "op",
            "_triggering_element_value": "Find",
            "ajax_html_ids[]": [
                "ntc-web-my",
                "skip-link",
                "navbar",
                "navbar-collapse",
                "search-block-form",
                "ntc-web-search-input-label",
                "ntc-web-search-input",
                "ui-id-1",
                "ntc-web-main",
                "main-content",
                "block-system-main",
                "web-drupal-content",
                "web-drupal-content-main",
                "node-4024",
                "block-ntc-address-ntc-address-finder",
                "wizard-form-wrapper",
                "ntc-address-wizard",
                "edit-postcode",
                "edit-find",
                "backtotop",
            ],
            "ajax_page_state[theme]": "ntc_bootstrap",
            "ajax_page_state[theme_token]": "LN05JIzI6rocWDiBpDyVeywYveuS4jlxD_N0_hhp2Ko",
            "ajax_page_state[css][0]": "1",
            "ajax_page_state[css][modules/system/system.base.css]": "1",
            "ajax_page_state[css][misc/ui/jquery.ui.core.css]": "1",
            "ajax_page_state[css][misc/ui/jquery.ui.theme.css]": "1",
            "ajax_page_state[css][misc/ui/jquery.ui.menu.css]": "1",
            "ajax_page_state[css][misc/ui/jquery.ui.autocomplete.css]": "1",
            "ajax_page_state[css][sites/all/modules/calendar/css/calendar_multiday.css]": "1",
            "ajax_page_state[css][sites/all/modules/date/date_repeat_field/date_repeat_field.css]": "1",
            "ajax_page_state[css][modules/field/theme/field.css]": "1",
            "ajax_page_state[css][modules/node/node.css]": "1",
            "ajax_page_state[css][sites/all/modules/youtube/css/youtube.css]": "1",
            "ajax_page_state[css][sites/all/modules/views/css/views.css]": "1",
            "ajax_page_state[css][sites/all/modules/back_to_top/css/back_to_top.css]": "1",
            "ajax_page_state[css][sites/all/modules/ckeditor/css/ckeditor.css]": "1",
            "ajax_page_state[css][sites/all/modules/ctools/css/ctools.css]": "1",
            "ajax_page_state[css][sites/all/modules/panels/css/panels.css]": "1",
            "ajax_page_state[css][sites/all/modules/taxonomy_access/taxonomy_access.css]": "1",
            "ajax_page_state[css][sites/all/modules/search_autocomplete/css/themes/minimal.css]": "1",
            "ajax_page_state[css][sites/all/themes/ntc_bootstrap/css/bootstrap.css]": "1",
            "ajax_page_state[css][sites/all/themes/ntc_bootstrap/css/generic.css]": "1",
            "ajax_page_state[css][sites/all/themes/ntc_bootstrap/css/custom.css]": "1",
            "ajax_page_state[css][sites/all/themes/ntc_bootstrap/css/components.css]": "1",
            "ajax_page_state[css][sites/all/themes/ntc_bootstrap/css/modules.css]": "1",
            "ajax_page_state[css][sites/all/themes/ntc_bootstrap/css/fostering.css]": "1",
            "ajax_page_state[css][sites/all/themes/ntc_bootstrap/css/responsive.css]": "1",
            "ajax_page_state[css][sites/all/themes/ntc_bootstrap/css/ie10.css]": "1",
            "ajax_page_state[css][sites/all/themes/ntc_bootstrap/css/ie.css]": "1",
            "ajax_page_state[js][0]": "1",
            "ajax_page_state[js][1]": "1",
            "ajax_page_state[js][sites/all/themes/bootstrap/js/bootstrap.js]": "1",
            "ajax_page_state[js][//ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js]": "1",
            "ajax_page_state[js][misc/jquery-extend-3.4.0.js]": "1",
            "ajax_page_state[js][misc/jquery-html-prefilter-3.5.0-backport.js]": "1",
            "ajax_page_state[js][misc/jquery.once.js]": "1",
            "ajax_page_state[js][misc/drupal.js]": "1",
            "ajax_page_state[js][//ajax.googleapis.com/ajax/libs/jqueryui/1.10.2/jquery-ui.min.js]": "1",
            "ajax_page_state[js][sites/all/modules/jquery_update/replace/ui/external/jquery.cookie.js]": "1",
            "ajax_page_state[js][sites/all/modules/jquery_update/replace/misc/jquery.form.min.js]": "1",
            "ajax_page_state[js][misc/ajax.js]": "1",
            "ajax_page_state[js][sites/all/modules/jquery_update/js/jquery_update.js]": "1",
            "ajax_page_state[js][sites/all/modules/back_to_top/js/back_to_top.js]": "1",
            "ajax_page_state[js][sites/all/themes/bootstrap/js/misc/_progress.js]": "1",
            "ajax_page_state[js][sites/all/modules/field_group/field_group.js]": "1",
            "ajax_page_state[js][sites/all/modules/search_autocomplete/js/jquery.autocomplete.js]": "1",
            "ajax_page_state[js][sites/all/themes/ntc_bootstrap/scripts/NTC.jquery.contentMenuScroller.js]": "1",
            "ajax_page_state[js][sites/all/themes/ntc_bootstrap/scripts/NTC.jquery.alertClose.js]": "1",
            "ajax_page_state[js][sites/all/themes/ntc_bootstrap/scripts/NTC.jquery.activeTrail.js]": "1",
            "ajax_page_state[js][sites/all/themes/ntc_bootstrap/scripts/NTC.jquery.expandLinkToDiv.js]": "1",
            "ajax_page_state[js][sites/all/themes/ntc_bootstrap/scripts/NTC.jquery.events.js]": "1",
            "ajax_page_state[js][sites/all/themes/ntc_bootstrap/scripts/cookieconsent.js]": "1",
            "ajax_page_state[js][sites/all/themes/ntc_bootstrap/scripts/google-analytics.js]": "1",
            "ajax_page_state[js][sites/all/themes/ntc_bootstrap/scripts/ios-orientationchange-fix.js]": "1",
            "ajax_page_state[js][sites/all/themes/bootstrap/js/misc/ajax.js]": "1",
            "ajax_page_state[jquery_version]": "1.10",
        }
        uprn_data = {
            "house_number": "0000" + f"{user_uprn}",
            "op": "Use",
            "form_build_id": "form-BQ47tM0NKADE0s8toYkdSef3QBn6lDM-yBseqIOho80",
            "form_id": "ntc_address_wizard",
        }
        collections = []

        response = s.post(
            "https://my.northtyneside.gov.uk/system/ajax",
            # cookies=cookies,
            headers=headers,
            data=ajax_data,
            verify=False,
        )
        response = s.post(
            "https://my.northtyneside.gov.uk/category/81/bin-collection-dates",
            # cookies=cookies,
            headers=headers,
            data=uprn_data,
            verify=False,
        )
        response = s.get(
            "https://my.northtyneside.gov.uk/category/81/bin-collection-dates",
            # cookies=cookies,
            headers=headers,
            data=uprn_data,
            verify=False,
        )

        # Parse form page and get the day of week text
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()
        bin_text = soup.find("section", {"class": "block block-ntc-bins clearfix"})
        regular_text = bin_text.select("p:nth-child(2) > strong")[0].text.strip()
        x = bin_text.select("p:nth-child(4) > strong")
        if len(bin_text.select("p:nth-child(4) > strong")) == 1:
            special_text = bin_text.select("p:nth-child(4) > strong")[0].text.strip()
        else:
            special_text = bin_text.select("p:nth-child(5) > strong")[0].text.strip()

        # Since calendar only shows until end of March 2024, work out how many weeks that is
        weeks_total = math.floor((datetime(2024, 4, 1) - datetime.now()).days / 7)

        # Convert day text to series of dates using previous calculation
        regular_collections = get_weekday_dates_in_period(
            datetime.today(),
            days_of_week.get(regular_text.capitalize()),
            amount=weeks_total,
        )
        special_collections = get_weekday_dates_in_period(
            datetime.today(), days_of_week.get(special_text.capitalize())
        )

        # Differentiate between regular and recycling bins
        for item in regular_collections:
            item_as_date = datetime.strptime(item, date_format)
            # Check if holiday (calendar only has one day that's a holiday, and it's moved to the next day)
            if is_holiday(item_as_date, Region.ENG):
                item_as_date += timedelta(days=1)
            # Use the isoweek number to separate collections - at the time of writing 11th Jan is week 2, which
            # is for the grey bin
            if (item_as_date.date().isocalendar()[1] % 2) == 0:
                collections.append(("Regular bin (green)", item_as_date))

            else:
                collections.append(("Recycling bin (grey)", item_as_date))

        # Add the special collection dates to the collection tuple
        collections += [
            ("Special collection (bookable)", datetime.strptime(item, date_format))
            for item in special_collections
        ]

        # Sort the collections tuple by date, the add to dictionary and return
        ordered_data = sorted(collections, key=lambda x: x[1])
        data = {"bins": []}
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
