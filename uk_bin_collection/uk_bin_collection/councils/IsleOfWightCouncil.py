import hashlib
import os
import re
import tempfile
import time
from collections import defaultdict
from datetime import datetime

import pdfplumber
import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

RECYCLING_COLORS = [
    (0.5, 0.0, 1.0, 0.0),  # CMYK purple (2024-25 PDF)
    (0.584, 0.757, 0.12),  # RGB green (2025-26 and 2026-27 PDFs)
]
NON_RECYCLABLE_COLORS = [
    (0.0, 0.0, 0.0, 0.383),  # CMYK grey (2024-25 PDF)
    (0.713, 0.713, 0.712),  # RGB grey (2025-26 and 2026-27 PDFs)
]
HEADER_BG_COLORS = [
    (0.527, 0.323, 0.0, 0.0),  # CMYK brown (2024-25 PDF)
    (0.525, 0.628, 0.828),  # RGB blue (2025-26 and 2026-27 PDFs)
]
# The third key in the calendar legend, alongside "Recycling day" and
# "General Waste day". A bank holiday cell carries no collection: the council
# publishes the revised dates separately rather than in the calendar grid.
BANK_HOLIDAY_COLORS = [
    (1.0, 1.0, 1.0),  # white (2026-27 PDF)
]
COLOR_TOLERANCE = 0.08

MONTHS = [
    "JANUARY",
    "FEBRUARY",
    "MARCH",
    "APRIL",
    "MAY",
    "JUNE",
    "JULY",
    "AUGUST",
    "SEPTEMBER",
    "OCTOBER",
    "NOVEMBER",
    "DECEMBER",
]

WEEKDAYS = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}

PDF_CACHE_DIR = os.path.join(tempfile.gettempdir(), "iow-pdf-cache")
PDF_CACHE_MAX_AGE = 86400 * 7

# The "View Collection Calendar" button is a Blazor Server click handler with
# no href: the server calls triggerFileDownload() from /js/WasteDay/wasteDay.js
# over SignalR, which builds an <a download href="...pdf"> and clicks it. The
# anchor's click is hooked rather than triggerFileDownload itself because
# Blazor caches the interop function it resolved off window, so replacing that
# function has no effect once the page has called it. Swallowing the click also
# keeps the browser from actually downloading the PDF, which we fetch ourselves.
CALENDAR_URL_HOOK = """
window.__ukbcdCalendarUrl = null;
const anchorClick = HTMLAnchorElement.prototype.click;
HTMLAnchorElement.prototype.click = function () {
    if (this.download || /\\.pdf($|[?#])/i.test(this.href)) {
        window.__ukbcdCalendarUrl = this.href;
        return;
    }
    return anchorClick.apply(this, arguments);
};
"""


def _color_match(c1, c2, tol=COLOR_TOLERANCE):
    if not isinstance(c1, tuple) or not isinstance(c2, tuple):
        return False
    if len(c1) != len(c2):
        return False
    return all(abs(a - b) <= tol for a, b in zip(c1, c2))


def _color_in_list(color, color_list, tol=COLOR_TOLERANCE):
    return any(_color_match(color, ref, tol) for ref in color_list)


def _get_bg_color(x, y, rects):
    best = None
    best_area = float("inf")
    for r in rects:
        if r["x0"] <= x <= r["x1"] and r["top"] <= y <= r["bottom"]:
            rc = r.get("non_stroking_color")
            if rc and isinstance(rc, tuple) and len(rc) >= 3:
                area = (r["x1"] - r["x0"]) * (r["bottom"] - r["top"])
                if area < best_area:
                    best_area = area
                    best = rc
    return best


def _merge_split_words(words):
    """Join alphabetic word fragments that the PDF splits mid-word.

    The 2026-27 calendar emits SEPTEMBER as two words, "SEPTEMB" and "ER",
    with no gap between them, which stops the month header matching by name.
    Only touching letters are joined, so a month and the year beside it
    ("AUGUST", "2026") stay separate.
    """
    merged = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and w["text"].isalpha()
            and prev["text"].isalpha()
            and abs(prev["top"] - w["top"]) < 2
            and 0 <= w["x0"] - prev["x1"] < 1.5
        ):
            merged[-1] = {**prev, "text": prev["text"] + w["text"], "x1": w["x1"]}
        else:
            merged.append(dict(w))
    return merged


def _find_month_headers(words):
    """Find each month grid's header, e.g. "DECEMBER 2026".

    Grid headers are upper case, which is what separates them from the same
    month names in the surrounding prose ("Runs May 2026 to April 2027", "The
    crew may arrive any time"). The year is read from the word beside the
    month, so a calendar spanning a year boundary needs no guessing.
    """
    headers = []
    merged = _merge_split_words(words)
    for i, w in enumerate(merged):
        if not w["text"].isupper() or w["text"] not in MONTHS:
            continue
        year = None
        for nxt in merged[i + 1 : i + 3]:
            if (
                abs(nxt["top"] - w["top"]) < 2
                and 0 <= nxt["x0"] - w["x1"] < 10
                and re.fullmatch(r"20\d{2}", nxt["text"])
            ):
                year = int(nxt["text"])
                break
        headers.append(
            {
                "month": MONTHS.index(w["text"]) + 1,
                "year": year,
                "x0": w["x0"],
                "top": w["top"],
                "bottom": w.get("bottom", w["top"] + 12),
            }
        )

    if not headers:
        raise ValueError("No month headers found in PDF calendar")

    _assign_missing_years(headers)
    return headers


def _assign_missing_years(headers):
    """Fill in any header whose year did not parse, from its neighbours.

    The grids are laid out in chronological order, so a missing year follows
    from the month either side of it.
    """
    if not any(h["year"] for h in headers):
        raise ValueError("No year found beside any month header in PDF calendar")

    for i in range(1, len(headers)):
        if headers[i]["year"] is None and headers[i - 1]["year"] is not None:
            rolled = headers[i]["month"] < headers[i - 1]["month"]
            headers[i]["year"] = headers[i - 1]["year"] + (1 if rolled else 0)
    for i in range(len(headers) - 2, -1, -1):
        if headers[i]["year"] is None and headers[i + 1]["year"] is not None:
            rolled = headers[i]["month"] > headers[i + 1]["month"]
            headers[i]["year"] = headers[i + 1]["year"] - (1 if rolled else 0)


def _column_index(x, page_width):
    """Which of the calendar's three grid columns an x coordinate falls in.

    Returns -1 for anything off the page, which is where the rotated prose in
    the left-hand panel ends up.
    """
    if x < 0 or x > page_width:
        return -1
    return min(int(x / (page_width / 3)), 2)


def _parse_calendar_pdf(pdf_path, collection_day):
    pdf = pdfplumber.open(pdf_path)
    page = pdf.pages[0]

    rects = page.rects
    words = page.extract_words()
    page_width = page.width

    target_weekday = WEEKDAYS.get(collection_day.upper())
    if target_weekday is None:
        raise ValueError(f"Unknown collection day: {collection_day}")

    month_headers = _find_month_headers(words)

    day_header_rows = defaultdict(list)
    for w in words:
        if w["text"] in ("M", "T", "W", "F", "S") and w["top"] > 130:
            y_key = round(w["top"] / 5) * 5
            day_header_rows[y_key].append(w)

    month_col_x = {}
    for mh in month_headers:
        col_group = _column_index(mh["x0"], page_width)
        if col_group < 0:
            continue

        best_row_y = None
        best_dist = float("inf")
        for y_key in day_header_rows:
            if y_key < mh["top"]:
                continue
            dist = y_key - mh["top"]
            if dist < best_dist and dist < 30:
                best_dist = dist
                best_row_y = y_key

        if best_row_y is None:
            continue

        col_words = sorted(
            [
                w
                for w in day_header_rows[best_row_y]
                if _column_index(w["x0"], page_width) == col_group
            ],
            key=lambda w: w["x0"],
        )
        if len(col_words) < 7:
            continue

        target_word = col_words[target_weekday]
        month_col_x[(mh["year"], mh["month"])] = {
            "x_center": (target_word["x0"] + target_word["x1"]) / 2,
            "header_bottom": col_words[0].get("bottom", col_words[0]["top"] + 10),
        }

    if not month_col_x:
        raise ValueError("No month grids found in PDF calendar")

    results = []
    for (year, month), col_info in month_col_x.items():
        col_x = col_info["x_center"]
        header_y = col_info["header_bottom"]

        for w in words:
            if w["top"] <= header_y or w["top"] > header_y + 80:
                continue

            word_center = (w["x0"] + w["x1"]) / 2
            if abs(word_center - col_x) > 10:
                continue

            if not w["text"].strip().isdigit():
                continue

            day_num = int(w["text"].strip())
            try:
                dt = datetime(year, month, day_num)
            except ValueError:
                continue

            if dt.weekday() != target_weekday:
                continue

            wx = word_center
            wy = (w["top"] + w.get("bottom", w["top"] + 10)) / 2
            bg = _get_bg_color(wx, wy, rects)

            if _color_in_list(bg, RECYCLING_COLORS):
                bin_type = "Recycling"
            elif _color_in_list(bg, NON_RECYCLABLE_COLORS):
                bin_type = "Non-recyclable waste"
            elif _color_in_list(bg, HEADER_BG_COLORS):
                continue
            elif _color_in_list(bg, BANK_HOLIDAY_COLORS):
                # Bank holiday: no collection shown for this round that week.
                continue
            else:
                raise ValueError(
                    f"Unknown calendar colour {bg} at day {day_num} {year}-{month:02d}"
                )

            results.append((dt, bin_type))

    results.sort()
    return results


def _download_pdf_cached(pdf_url, cookies=None, headers=None):
    os.makedirs(PDF_CACHE_DIR, exist_ok=True)
    url_hash = hashlib.md5(pdf_url.encode(), usedforsecurity=False).hexdigest()[:12]
    pdf_path = os.path.join(PDF_CACHE_DIR, f"iow_{url_hash}.pdf")

    if os.path.exists(pdf_path):
        age = time.time() - os.path.getmtime(pdf_path)
        if age < PDF_CACHE_MAX_AGE:
            return pdf_path

    resp = requests.get(
        pdf_url,
        cookies=cookies or {},
        headers=headers or {},
        timeout=30,
        allow_redirects=True,
    )

    if resp.status_code != 200 or resp.content[:4] != b"%PDF":
        raise ValueError(
            f"Could not download PDF from {pdf_url} (status {resp.status_code})"
        )

    tmp_path = pdf_path + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(resp.content)
    os.replace(tmp_path, pdf_path)

    return pdf_path


def _select_address(options_text, user_paon):
    """Pick the best address from a list of option labels."""
    if user_paon:
        paon_lower = user_paon.lower().strip()
        for label in options_text:
            if label.lower().startswith(paon_lower + ",") or label.lower().startswith(
                paon_lower + " "
            ):
                return label

    for label in options_text:
        if "addresses found" not in label:
            return label

    return None


def _extract_collection_day(html):
    """Parse the collection weekday from the results page HTML."""
    soup = BeautifulSoup(html, features="html.parser")

    collection_day_el = soup.find("strong", string=re.compile(r"Collection Day:"))
    if collection_day_el:
        return (
            collection_day_el.parent.get_text().replace("Collection Day:", "").strip()
        )

    if soup.find(string=re.compile(r"no waste collection details", re.I)):
        # e.g. non-domestic properties: "Sorry, no waste collection details
        # are currently available for this property"
        raise ValueError(
            "Isle of Wight Council has no waste collection details for this "
            "property - check the address is a domestic property"
        )

    raise ValueError("Could not find collection day in page")


def _build_bins(collection_dates):
    """Filter to future dates and format for UKBCD output."""
    data = {"bins": []}
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for dt, bin_type in collection_dates:
        if dt >= today:
            data["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": dt.strftime(date_format),
                }
            )

    return data


class CouncilClass(AbstractGetBinDataClass):
    """
    Isle of Wight Council scraper.
    Uses Selenium to navigate a Blazor Server form, then downloads and
    parses the colour-coded PDF collection calendar the results page offers.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import Select, WebDriverWait

        driver = None
        try:
            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_postcode(user_postcode)

            url = "https://digitalservices.iow.gov.uk/wasteday"
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(url)

            wait = WebDriverWait(driver, 30)

            wait.until(EC.presence_of_element_located((By.ID, "Postcode")))
            # This is a Blazor Server page - the postcode field is present in
            # the initial static render, then gets replaced wholesale once
            # the SignalR connection hydrates it, which invalidates the
            # WebElement reference grabbed above (StaleElementReferenceException).
            # Settle briefly, then re-fetch the (now-interactive) element.
            time.sleep(2)
            postcode_input = wait.until(
                EC.presence_of_element_located((By.ID, "Postcode"))
            )
            postcode_input.clear()
            postcode_input.send_keys(user_postcode)

            find_btn = driver.find_element(
                By.XPATH, "//button[contains(text(), 'Find address')]"
            )
            find_btn.click()

            address_select = wait.until(
                EC.presence_of_element_located((By.ID, "SelectAddress"))
            )

            time.sleep(2)
            select = Select(address_select)
            options_text = [opt.text.strip() for opt in select.options]

            target_label = _select_address(options_text, user_paon)
            if not target_label:
                raise ValueError(f"No addresses found for {user_postcode}")

            select.select_by_visible_text(target_label)

            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h2[contains(text(), 'Collection Details')]")
                )
            )
            time.sleep(1)

            collection_day = _extract_collection_day(driver.page_source)

            # The calendar PDF's URL only exists inside the Blazor circuit, so
            # it has to be clicked out of the page rather than read from a link.
            driver.execute_script(CALENDAR_URL_HOOK)
            calendar_btn = driver.find_element(
                By.XPATH, "//button[contains(., 'View Collection Calendar')]"
            )
            driver.execute_script("arguments[0].click();", calendar_btn)
            try:
                wait.until(
                    lambda d: d.execute_script("return window.__ukbcdCalendarUrl;")
                )
            except TimeoutException:
                raise ValueError(
                    "The 'View Collection Calendar' button did not produce a "
                    "PDF link - the council's download mechanism has changed"
                )
            pdf_url = driver.execute_script("return window.__ukbcdCalendarUrl;")

            cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
            ua = driver.execute_script("return navigator.userAgent;")
            headers = {
                "User-Agent": ua,
                "Referer": url,
            }

            pdf_path = _download_pdf_cached(pdf_url, cookies=cookies, headers=headers)
            collection_dates = _parse_calendar_pdf(pdf_path, collection_day)
            if not collection_dates:
                raise ValueError(
                    f"No {collection_day} collections found in the calendar at {pdf_url}"
                )
            return _build_bins(collection_dates)

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
