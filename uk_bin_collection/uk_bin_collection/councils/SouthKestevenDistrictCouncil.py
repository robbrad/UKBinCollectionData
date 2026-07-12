import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests
from requests import RequestException
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from uk_bin_collection.uk_bin_collection.common import create_webdriver, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """South Kesteven District Council bin collections via the live binday flow."""

    BIN_DAY_URL = "https://www.southkesteven.gov.uk/binday"
    CHECKER_LINK_TEXT = "Postcode bin day checker"
    BIN_TYPE_MAP = {
        "240 Litre Recycling": "Grey Bin",
        "23lt Food Caddy": "Food Bin",
        "240 Litre Refuse": "Black Bin",
        "240 Litre Paper and Card": "Purple Bin",
    }
    ADDRESS_VALUE_ID = "FF5265"
    POSTCODE_INPUT_ID = "FF5265-text"
    SEARCH_BUTTON_ID = "FF5265-find"
    ADDRESS_SELECT_ID = "FF5265-list"
    ADDRESS_DISPLAY_ID = "FF5265-displayname"
    CHANGE_BUTTON_ID = "FF5265-change"
    SUBMIT_BUTTON_ID = "submit-button"
    BODY_CONTENT_ID = "body-content"
    CURRENT_SECTION_ID = "current-section-id"
    DEFAULT_ARTIFACT_ROOT = "artifacts/SouthKestevenDistrictCouncil"

    def parse_data(self, page: str, **kwargs) -> dict:
        binday_url = kwargs.get("url") or self.BIN_DAY_URL
        postcode = kwargs.get("postcode")
        paon = kwargs.get("paon")
        web_driver = kwargs.get("web_driver")
        user_agent = kwargs.get("user_agent")
        headless = kwargs.get("headless", True)
        artifact_root = self._get_artifact_root(kwargs.get("artifact_dir"))

        if headless is None:
            headless = True

        if not postcode:
            raise ValueError("Postcode is required for South Kesteven.")
        if not paon:
            raise ValueError(
                "Property number or name (paon) is required for South Kesteven."
            )

        checker_url = self._resolve_checker_url(binday_url, page=page, user_agent=user_agent)

        driver = create_webdriver(web_driver, headless, user_agent, __name__)
        try:
            wait = WebDriverWait(driver, 30)
            driver.get(checker_url)

            postcode_input = self._wait_for_clickable(
                wait,
                (By.ID, self.POSTCODE_INPUT_ID),
                "Unable to find the postcode input on the South Kesteven checker.",
            )
            postcode_input.clear()
            postcode_input.send_keys(postcode)

            initial_section_id = self._get_current_section_id(driver)
            initial_body_markup = self._get_body_markup(driver)

            search_button = self._wait_for_clickable(
                wait,
                (By.ID, self.SEARCH_BUTTON_ID),
                "Unable to find the search button after entering the postcode.",
            )
            search_button.click()

            address_select = self._wait_for_address_options(wait)
            self._select_address(address_select, paon)
            self._wait_for_address_confirmation(wait)

            submit_button = self._wait_for_clickable(
                wait,
                (By.ID, self.SUBMIT_BUTTON_ID),
                "Unable to find the submit button after selecting the address.",
            )
            submit_button.click()
            self._wait_for_results_container(
                wait,
                initial_section_id,
                initial_body_markup,
            )

            return {"bins": self._parse_collection_rows(driver.page_source)}
        except Exception as exc:
            artifact_path = self._capture_debug_artifacts(
                driver,
                artifact_root,
                {"postcode": postcode, "paon": paon, "binday_url": binday_url},
            )
            raise RuntimeError(
                self._with_artifact_hint(str(exc), artifact_path)
            ) from exc
        finally:
            if driver:
                driver.quit()

    def _wait_for_clickable(self, wait, locator, error_message):
        try:
            return wait.until(EC.element_to_be_clickable(locator))
        except TimeoutException as exc:
            raise RuntimeError(error_message) from exc

    def _wait_for_presence(self, wait, locator, error_message):
        try:
            return wait.until(EC.presence_of_element_located(locator))
        except TimeoutException as exc:
            raise RuntimeError(error_message) from exc

    def _resolve_checker_url(
        self, binday_url: str, page: str | object | None = None, user_agent: str | None = None
    ) -> str:
        html = self._get_binday_html(binday_url, page=page, user_agent=user_agent)
        soup = BeautifulSoup(html, "html.parser")

        for link in soup.find_all("a", href=True):
            link_text = link.get_text(" ", strip=True).lower()
            if self.CHECKER_LINK_TEXT.lower() in link_text:
                return urljoin(binday_url, link["href"])

        raise RuntimeError(
            "Unable to find the postcode bin day checker link on the binday page."
        )

    def _get_binday_html(
        self, binday_url: str, page: str | object | None = None, user_agent: str | None = None
    ) -> str:
        if hasattr(page, "text"):
            html = str(page.text)
        elif isinstance(page, str) and page.strip():
            html = page
        else:
            headers = {}
            if user_agent:
                headers["User-Agent"] = user_agent
            try:
                response = requests.get(binday_url, headers=headers, timeout=30)
                response.raise_for_status()
            except RequestException as exc:
                raise RuntimeError(
                    f"Unable to load the South Kesteven binday page at {binday_url}."
                ) from exc
            html = response.text

        if not html.strip():
            raise RuntimeError(
                f"Unable to load the South Kesteven binday page at {binday_url}."
            )

        return html

    def _wait_for_address_options(self, wait):
        try:
            return wait.until(self._address_options_ready)
        except TimeoutException as exc:
            raise RuntimeError(
                "Unable to find the address dropdown after searching for the postcode."
            ) from exc

    def _address_options_ready(self, driver):
        try:
            address_select = driver.find_element(By.ID, self.ADDRESS_SELECT_ID)
        except NoSuchElementException:
            return False

        if not address_select.is_displayed():
            return False

        options = [option for option in Select(address_select).options if option.text.strip()]
        return address_select if options else False

    def _wait_for_address_confirmation(self, wait):
        try:
            return wait.until(self._address_confirmation_ready)
        except TimeoutException as exc:
            raise RuntimeError(
                "Unable to confirm the selected address before submitting the lookup."
            ) from exc

    def _address_confirmation_ready(self, driver):
        try:
            address_value = driver.find_element(By.ID, self.ADDRESS_VALUE_ID)
            change_button = driver.find_element(By.ID, self.CHANGE_BUTTON_ID)
        except NoSuchElementException:
            return False

        selected_value = (address_value.get_attribute("value") or "").strip()
        if selected_value and change_button.is_displayed():
            return True

        try:
            display_name = driver.find_element(By.ID, self.ADDRESS_DISPLAY_ID)
        except NoSuchElementException:
            return False

        return bool((display_name.text or "").strip()) and change_button.is_displayed()

    def _wait_for_results_container(
        self, wait, initial_section_id: str | None, initial_body_markup: str
    ):
        try:
            return wait.until(
                lambda driver: self._results_container_ready(
                    driver,
                    initial_section_id,
                    initial_body_markup,
                )
            )
        except TimeoutException as exc:
            raise RuntimeError(
                "Unable to load the collection results after submitting the address."
            ) from exc

    def _results_container_ready(
        self, driver, initial_section_id: str | None, initial_body_markup: str
    ):
        try:
            body_markup = self._get_body_markup(driver)
        except RuntimeError:
            return False

        if not body_markup or body_markup == initial_body_markup:
            return False

        current_section_id = self._get_current_section_id(driver)
        section_changed = bool(
            initial_section_id and current_section_id and current_section_id != initial_section_id
        )
        address_form_gone = self.POSTCODE_INPUT_ID not in body_markup
        has_collection_markup = "alloy-table" in body_markup.lower() or "your collections" in body_markup.lower()

        return address_form_gone and (section_changed or has_collection_markup)

    def _select_address(self, address_select, paon: str) -> None:
        target = str(paon).strip().lower()
        select = Select(address_select)

        for option in select.options:
            option_text = option.text.strip().lower()
            if target in option_text:
                select.select_by_visible_text(option.text)
                return

        raise RuntimeError(
            f"Unable to find the property '{paon}' in the address dropdown."
        )

    def _get_current_section_id(self, driver) -> str | None:
        try:
            return driver.find_element(By.ID, self.CURRENT_SECTION_ID).get_attribute("value")
        except NoSuchElementException:
            return None

    def _get_body_markup(self, driver) -> str:
        try:
            body_content = driver.find_element(By.ID, self.BODY_CONTENT_ID)
        except NoSuchElementException as exc:
            raise RuntimeError("Unable to find the body-content container on the checker page.") from exc

        return body_content.get_attribute("innerHTML") or ""

    def _get_artifact_root(self, artifact_dir: str | None) -> Path:
        if artifact_dir:
            return Path(artifact_dir)
        return Path.cwd() / self.DEFAULT_ARTIFACT_ROOT

    def _capture_debug_artifacts(
        self, driver, artifact_root: Path, context: dict[str, str]
    ) -> Path | None:
        if not driver:
            return None

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        artifact_path = artifact_root / timestamp
        artifact_path.mkdir(parents=True, exist_ok=True)

        metadata = {
            "current_url": str(getattr(driver, "current_url", "")) or None,
            **context,
        }

        screenshot_path = artifact_path / "page.png"
        html_path = artifact_path / "page.html"
        metadata_path = artifact_path / "metadata.json"

        try:
            html_path.write_text(driver.page_source, encoding="utf-8")
        except Exception as exc:
            metadata["page_html_error"] = str(exc)

        try:
            metadata["screenshot_saved"] = bool(driver.save_screenshot(str(screenshot_path)))
        except Exception as exc:
            metadata["screenshot_error"] = str(exc)

        metadata_path.write_text(json.dumps(metadata, indent=4), encoding="utf-8")
        return artifact_path.resolve()

    def _with_artifact_hint(self, message: str, artifact_path: Path | None) -> str:
        if artifact_path is None:
            return message
        return f"{message} Debug artifacts saved to: {artifact_path}"

    def _normalize_bin_type(self, raw_bin_type: str) -> str:
        return self.BIN_TYPE_MAP.get(raw_bin_type, raw_bin_type)

    def _parse_collection_rows(self, page_source: str) -> list[dict]:
        soup = BeautifulSoup(page_source, "html.parser")
        bins = []

        body_content = soup.find(id=self.BODY_CONTENT_ID) or soup
        for table in body_content.find_all("table"):
            for row in table.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) < 2:
                    continue

                raw_date = cols[0].get_text(" ", strip=True).replace(",", "")
                raw_bin_type = cols[1].get_text(" ", strip=True)

                try:
                    collection_date = datetime.strptime(
                        raw_date, "%A %d %B %Y"
                    ).strftime(date_format)
                except ValueError:
                    continue

                bins.append(
                    {
                        "type": self._normalize_bin_type(raw_bin_type),
                        "collectionDate": collection_date,
                    }
                )

        if not bins:
            raise RuntimeError(
                "Unable to find any collection rows on the South Kesteven results page."
            )

        return bins
