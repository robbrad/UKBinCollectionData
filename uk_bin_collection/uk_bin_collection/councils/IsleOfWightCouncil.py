import os
import hashlib
import re
import time
from collections import defaultdict
from datetime import datetime

import pdfplumber
import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

RECYCLING_COLORS = [
    (0.5, 0.0, 1.0, 0.0),      # CMYK purple (2024-25 PDF)
    (0.584, 0.757, 0.12),       # RGB green (2025-26 PDF)
]
NON_RECYCLABLE_COLORS = [
    (0.0, 0.0, 0.0, 0.383),    # CMYK grey (2024-25 PDF)
    (0.713, 0.713, 0.712),      # RGB grey (2025-26 PDF)
]
HEADER_BG_COLORS = [
    (0.527, 0.323, 0.0, 0.0),  # CMYK brown (2024-25 PDF)
    (0.525, 0.628, 0.828),      # RGB blue (2025-26 PDF)
]
COLOR_TOLERANCE = 0.08

MONTHS = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
]

PDF_CACHE_DIR = "/tmp/iow-pdf-cache"
PDF_CACHE_MAX_AGE = 86400 * 7


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


def _parse_calendar_pdf(pdf_path, collection_day):
    pdf = pdfplumber.open(pdf_path)
    page = pdf.pages[0]
    text = page.extract_text() or ""

    year_matches = re.findall(r"20\d{2}", text[:300])
    start_year = int(year_matches[0]) if len(year_matches) >= 2 else datetime.now().year

    rects = page.rects
    words = page.extract_words()

    month_headers = []
    for w in words:
        upper = w["text"].upper()
        if upper in MONTHS:
            month_headers.append({
                "month": MONTHS.index(upper) + 1,
                "x0": w["x0"],
                "top": w["top"],
                "bottom": w.get("bottom", w["top"] + 12),
            })

    if not month_headers:
        return []

    first_month = month_headers[0]["month"]
    for mh in month_headers:
        mh["year"] = start_year if mh["month"] >= first_month else start_year + 1

    day_map = {
        "MONDAY": 0, "TUESDAY": 1, "WEDNESDAY": 2,
        "THURSDAY": 3, "FRIDAY": 4, "SATURDAY": 5, "SUNDAY": 6,
    }
    target_weekday = day_map.get(collection_day.upper())
    if target_weekday is None:
        return []

    COL_BOUNDARIES = [(0, 145), (145, 275), (275, 420)]

    def get_col(x):
        for i, (lo, hi) in enumerate(COL_BOUNDARIES):
            if lo <= x <= hi:
                return i
        return -1

    day_header_rows = defaultdict(list)
    for w in words:
        if w["text"] in ("M", "T", "W", "F", "S") and w["top"] > 130:
            y_key = round(w["top"] / 5) * 5
            day_header_rows[y_key].append(w)

    month_col_x = {}
    for mh in month_headers:
        col_group = get_col(mh["x0"])
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
            [w for w in day_header_rows[best_row_y] if get_col(w["x0"]) == col_group],
            key=lambda w: w["x0"],
        )
        if len(col_words) < 7:
            continue

        target_word = col_words[target_weekday]
        month_col_x[(mh["year"], mh["month"])] = {
            "x_center": (target_word["x0"] + target_word["x1"]) / 2,
            "header_bottom": col_words[0].get("bottom", col_words[0]["top"] + 10),
        }

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
            else:
                bin_type = "Collection"

            results.append((dt, bin_type))

    results.sort()
    return results


def _download_pdf_cached(pdf_url, cookies=None, headers=None):
    os.makedirs(PDF_CACHE_DIR, exist_ok=True)
    url_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:12]
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
        raise ValueError(f"Could not download PDF from {pdf_url} (status {resp.status_code})")

    with open(pdf_path, "wb") as f:
        f.write(resp.content)

    return pdf_path


def _select_address(options_text, user_paon):
    """Pick the best address from a list of option labels."""
    if user_paon:
        paon_lower = user_paon.lower().strip()
        for label in options_text:
            if label.lower().startswith(paon_lower + ",") or label.lower().startswith(paon_lower + " "):
                return label

    for label in options_text:
        if "addresses found" not in label:
            return label

    return None


def _extract_collection_info(html):
    """Parse collection day and PDF URL from the results page HTML."""
    soup = BeautifulSoup(html, features="html.parser")

    collection_day_el = soup.find("strong", string=re.compile(r"Collection Day:"))
    if collection_day_el:
        collection_day = collection_day_el.parent.get_text().replace("Collection Day:", "").strip()
    else:
        raise ValueError("Could not find collection day in page")

    pdf_link = soup.find("a", class_="download")
    if not pdf_link or not pdf_link.get("href"):
        raise ValueError("Could not find PDF calendar link")

    pdf_url = pdf_link["href"]
    if not pdf_url.startswith("http"):
        pdf_url = "https://www.iow.gov.uk" + pdf_url

    return collection_day, pdf_url


def _build_bins(collection_dates):
    """Filter to future dates and format for UKBCD output."""
    data = {"bins": []}
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for dt, bin_type in collection_dates:
        if dt >= today:
            data["bins"].append({
                "type": bin_type,
                "collectionDate": dt.strftime(date_format),
            })

    return data


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        if os.environ.get("UKBCD_USE_PLAYWRIGHT"):
            return self._parse_with_playwright(**kwargs)
        return self._parse_with_selenium(**kwargs)

    def _parse_with_playwright(self, **kwargs) -> dict:
        from playwright.sync_api import sync_playwright

        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        with sync_playwright() as pw:
            # Full Chromium required — headless shell can't run Blazor Server.
            # Must be launched under Xvfb (xvfb-run or DISPLAY set).
            pw_chromium = os.path.expanduser(
                "~/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome"
            )
            launch_kwargs = {
                "headless": False,
                "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            }
            if os.path.exists(pw_chromium):
                launch_kwargs["executable_path"] = pw_chromium
            browser = pw.chromium.launch(**launch_kwargs)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()
            try:
                page.goto(
                    "https://digitalservices.iow.gov.uk/wasteday",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

                page.wait_for_timeout(5000)

                page.locator("#Postcode").fill(user_postcode)
                page.wait_for_timeout(500)
                page.get_by_role("button", name="Find address").click()

                addr_select = page.locator("select")
                addr_select.wait_for(timeout=30000)
                page.wait_for_timeout(2000)

                options = page.locator("select option").all_text_contents()

                target_label = _select_address(options, user_paon)
                if not target_label:
                    raise ValueError(f"No addresses found for {user_postcode}")

                addr_select.select_option(label=target_label)

                page.get_by_role("heading", name="Collection Details").wait_for(
                    timeout=30000
                )
                page.wait_for_timeout(1000)

                html = page.content()
                soup = BeautifulSoup(html, features="html.parser")

                collection_day_el = soup.find(
                    "strong", string=re.compile(r"Collection Day:")
                )
                if not collection_day_el:
                    raise ValueError("Could not find collection day in page")
                collection_day = (
                    collection_day_el.parent.get_text()
                    .replace("Collection Day:", "")
                    .strip()
                )

                os.makedirs(PDF_CACHE_DIR, exist_ok=True)
                cache_key = hashlib.md5(
                    f"{user_postcode}_{collection_day}".encode()
                ).hexdigest()[:12]
                pdf_path = os.path.join(PDF_CACHE_DIR, f"iow_{cache_key}.pdf")

                need_download = True
                if os.path.exists(pdf_path):
                    age = time.time() - os.path.getmtime(pdf_path)
                    if age < PDF_CACHE_MAX_AGE:
                        need_download = False

                if need_download:
                    with page.expect_download(timeout=30000) as download_info:
                        page.get_by_role(
                            "button", name="View Collection Calendar"
                        ).click()
                    download = download_info.value
                    download.save_as(pdf_path)

                collection_dates = _parse_calendar_pdf(pdf_path, collection_day)
                return _build_bins(collection_dates)

            finally:
                browser.close()

    def _parse_with_selenium(self, **kwargs) -> dict:
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
            user_agent = (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            )
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(url)

            wait = WebDriverWait(driver, 30)

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
                EC.presence_of_element_located(
                    (By.XPATH, "//select[contains(@aria-label, 'Select an address')]")
                )
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

            html = driver.page_source
            collection_day, pdf_url = _extract_collection_info(html)

            cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
            user_agent = driver.execute_script("return navigator.userAgent;")
            headers = {
                "User-Agent": user_agent,
                "Referer": "https://digitalservices.iow.gov.uk/wasteday",
            }

            pdf_path = _download_pdf_cached(pdf_url, cookies=cookies, headers=headers)
            collection_dates = _parse_calendar_pdf(pdf_path, collection_day)
            return _build_bins(collection_dates)

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
