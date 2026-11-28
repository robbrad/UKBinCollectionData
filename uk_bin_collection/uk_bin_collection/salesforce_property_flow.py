"""Shared scraper for the Salesforce "waste collection enquiry" flow.

Cotswold, Forest of Dean and West Oxfordshire all run the same Experience
Cloud flow: type an address into a lookup, pick it from the dropdown, press
Next, read a Container / Collection day table.

The flow's markup lives inside nested Lightning Web Component shadow roots.
Document-level XPath lookups raise StaleElementReferenceException against it
and ChromeDriver cannot hand back elements from inside the shadow roots, so
every interaction here is done in page JavaScript (which can see through the
shadow roots) and only plain values cross back to Python.
"""

import re
import time
from datetime import date, datetime, timedelta

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

DATE_FORMAT = "%d/%m/%Y"
ADDRESS_INPUT = "input[role=combobox]"
ADDRESS_OPTION = "lightning-base-combobox-item[role=option]"
# The first dropdown entry is a "Show more results" action, not an address.
SEARCH_ACTION_VALUE = "actionAdvancedSearch"
PAGE_LOAD_TIMEOUT_SECONDS = 60
RESULTS_TIMEOUT_SECONDS = 60
TYPING_ATTEMPTS = 5

# Defines deep(selector): every match in the document and all nested shadow
# roots. A fresh page load discards it, so it is prepended to each script.
_DEEP_QUERY_JS = """
const deep = function (selector) {
    // A Set: the shadow roots can expose the same element more than once.
    const found = new Set();
    (function walk(root) {
        for (const el of root.querySelectorAll(selector)) found.add(el);
        for (const el of root.querySelectorAll('*')) {
            if (el.shadowRoot) walk(el.shadowRoot);
        }
    })(document);
    return [...found];
};
"""


class AddressNotFoundError(ValueError):
    """The dropdown offered no address matching the requested one."""


class AmbiguousAddressError(ValueError):
    """The dropdown offered more than one address matching the requested one."""


def _normalise_address(address: str) -> str:
    """Upper-case and drop commas and repeated whitespace for comparison."""
    return " ".join(address.replace(",", " ").upper().split())


def build_search_address(house_number: str, postcode: str) -> str:
    """Join house number/name and postcode unless the postcode is already in it."""
    house_number = (house_number or "").strip()
    postcode = (postcode or "").strip()
    if house_number and postcode:
        if _normalise_address(postcode) in _normalise_address(house_number):
            return house_number
        return f"{house_number}, {postcode}"
    return house_number or postcode


def select_address_option(
    options: list[dict], house_number: str, postcode: str
) -> dict:
    """Return the single dropdown option for this house number and postcode.

    `options` are dicts with "address" and "value". The address must start with
    `house_number` ending on a word boundary (so "24" matches "24 High St" but
    not "124 High St" or "24A High St") and contain `postcode` as a whole token.
    `house_number` may be a fuller address. Raises AddressNotFoundError for no
    match and AmbiguousAddressError for several, listing the candidates.
    """
    wanted = _normalise_address(house_number)
    if not wanted:
        raise AddressNotFoundError("No house number or address was supplied")
    starts_with = re.compile(rf"^{re.escape(wanted)}(?!\w)")
    has_postcode = re.compile(
        rf"(?<!\w){re.escape(_normalise_address(postcode))}(?!\w)"
    )
    matches = [
        option
        for option in options
        if starts_with.match(_normalise_address(option["address"]))
        and has_postcode.search(_normalise_address(option["address"]))
    ]
    if not matches:
        raise AddressNotFoundError(
            f"No address starting with {house_number!r} in {postcode!r} among: "
            f"{[option['address'] for option in options]}"
        )
    if len(matches) > 1:
        raise AmbiguousAddressError(
            f"{len(matches)} addresses start with {house_number!r} in {postcode!r}: "
            f"{[match['address'] for match in matches]}. Supply a fuller address."
        )
    return matches[0]


def parse_collection_day(raw_day: str, today: date | None = None) -> str:
    """Convert "Mon, 30 November", "Today" or "Tomorrow" to dd/mm/YYYY.

    The council gives no year, so a date already past rolls into next year. The
    weekday is ignored (it may be abbreviated or in full). Raises ValueError for
    text that is not a date.
    """
    today = today or date.today()
    text = raw_day.strip().lower()
    if text == "today":
        return today.strftime(DATE_FORMAT)
    if text == "tomorrow":
        return (today + timedelta(days=1)).strftime(DATE_FORMAT)
    found = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)", raw_day)
    if found:
        day, month = found.groups()
        for year in (today.year, today.year + 1):
            try:
                parsed = datetime.strptime(f"{day} {month} {year}", "%d %B %Y").date()
            except ValueError:
                # Not a real date this year (29 February) or not a month name.
                continue
            if parsed >= today:
                return parsed.strftime(DATE_FORMAT)
    raise ValueError(f"Cannot work out a collection date from {raw_day!r}")


def build_bins(rows: list[tuple[str, str]], today: date | None = None) -> dict:
    """Turn (container, collection day) table rows into the bins dict.

    Rows whose day is not a date (for example "Not collected") are skipped.
    Raises ValueError if no row yields a date, rather than returning no bins.
    """
    bins = []
    for container, raw_day in rows:
        try:
            collection_date = parse_collection_day(raw_day, today)
        except ValueError:
            continue
        bins.append({"type": container, "collectionDate": collection_date})
    if not bins:
        raise ValueError(f"No collection dates found in table rows: {rows}")
    return {"bins": bins}


def run_in_page(driver: WebDriver, script: str, *args: object) -> object:
    """Run JavaScript with deep(selector) available to pierce the shadow roots."""
    return driver.execute_script(_DEEP_QUERY_JS + script, *args)


def _type_address(driver: WebDriver, text: str) -> None:
    """Type `text` into the lookup, retrying if the page re-renders and drops it.

    The input appears before the flow finishes hydrating, and the first
    keystrokes can be lost when it re-renders, so confirm the value stuck.
    """
    for _ in range(TYPING_ATTEMPTS):
        run_in_page(
            driver,
            f"""
            const i = deep('{ADDRESS_INPUT}')[0];
            i.focus(); i.click();
            i.value = '';
            """,
        )
        ActionChains(driver).send_keys(text).perform()
        typed = run_in_page(
            driver, f"const i = deep('{ADDRESS_INPUT}')[0]; return i ? i.value : '';"
        )
        if typed == text:
            return
        time.sleep(2)
    raise RuntimeError(f"The address box did not keep the typed text {text!r}")


def fetch_collection_rows(
    driver: WebDriver, url: str, house_number: str, postcode: str
) -> list[tuple[str, str]]:
    """Drive the flow for one address and return (container, collection day) rows."""
    if not (house_number or "").strip() or not (postcode or "").strip():
        raise ValueError(
            "Both a house number (or full address) and postcode are required"
        )
    wanted = build_search_address(house_number, postcode)

    driver.get(url)
    WebDriverWait(driver, PAGE_LOAD_TIMEOUT_SECONDS).until(
        lambda d: run_in_page(d, f"return deep('{ADDRESS_INPUT}').length > 0")
    )
    _type_address(driver, wanted)

    option_script = f"""
        return deep('{ADDRESS_OPTION}')
            .filter(o => o.getAttribute('data-value') !== '{SEARCH_ACTION_VALUE}')
            .map(o => [o.innerText.split('\\n')[0].trim(), o.getAttribute('data-value')]);
    """
    WebDriverWait(driver, PAGE_LOAD_TIMEOUT_SECONDS).until(
        lambda d: run_in_page(d, option_script)
    )
    options = [
        {"address": address, "value": value}
        for address, value in run_in_page(driver, option_script)
    ]
    chosen = select_address_option(options, house_number, postcode)

    clicked = run_in_page(
        driver,
        f"""
        const target = arguments[0];
        const option = deep('{ADDRESS_OPTION}')
            .find(o => o.getAttribute('data-value') === target);
        if (!option) return false;
        option.click();
        return true;
        """,
        chosen["value"],
    )
    if not clicked:
        raise RuntimeError(f"Address option vanished before it was clicked: {chosen}")

    # Selecting an option fills the lookup; wait for that before pressing Next.
    WebDriverWait(driver, PAGE_LOAD_TIMEOUT_SECONDS).until(
        lambda d: run_in_page(
            d,
            f"const i = deep('{ADDRESS_INPUT}')[0]; return !!i && i.value.length > 0;",
        )
    )
    pressed = run_in_page(
        driver,
        """
        const next = deep('button').find(b => b.innerText.trim() === 'Next');
        if (!next) return false;
        next.click();
        return true;
        """,
    )
    if not pressed:
        raise RuntimeError("The Next button was not found after choosing the address")

    rows_script = """
        return deep('tr.slds-hint-parent').map(r => {
            const th = r.querySelector('th');
            const td = r.querySelector('td');
            return [
                th ? th.getAttribute('data-cell-value') : null,
                td ? td.getAttribute('data-cell-value') : null,
            ];
        });
    """
    # Navigation replaces the document, so poll rather than hold a reference.
    deadline = time.monotonic() + RESULTS_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        rows = run_in_page(driver, rows_script)
        if rows:
            return [(container, day) for container, day in rows if container and day]
        time.sleep(1)
    raise TimeoutError(
        f"No collection table appeared within {RESULTS_TIMEOUT_SECONDS}s"
    )
