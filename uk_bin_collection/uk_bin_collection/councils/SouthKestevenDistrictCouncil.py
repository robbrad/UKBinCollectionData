"""South Kesteven District Council collection data via its live browser flow."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from urllib.parse import quote, quote_plus, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import create_webdriver, date_format
from uk_bin_collection.uk_bin_collection.dependency_validation import (
    validate_websocket_client,
)
from uk_bin_collection.uk_bin_collection.exceptions import (
    AddressMismatchError,
    BrowserUnavailableError,
    ConfigurationError,
    MissingDependencyError,
    SiteChanged,
    UKBinCollectionError,
    UpstreamAccessDenied,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

_LOGGER = logging.getLogger(__name__)


class CouncilClass(AbstractGetBinDataClass):
    """Collect South Kesteven bin dates from the supported postcode checker."""

    # This adapter owns the complete browser navigation flow.  The opt-out is
    # intrinsic so callers cannot accidentally reinstate the direct HTTP
    # preflight that South Kesteven rejects in some environments.
    skip_generic_get = True
    BIN_DAY_URL = "https://www.southkesteven.gov.uk/binday"
    CHECKER_LINK_TEXT = "Postcode bin day checker"
    CHECKER_SCHEME = "https"
    CHECKER_HOST = "selfservice.southkesteven.gov.uk"
    PAGE_LOAD_TIMEOUT_SECONDS = 30
    ELEMENT_TIMEOUT_SECONDS = 30
    TOTAL_RUN_TIMEOUT_SECONDS = 90
    ACCESS_DENIED_MARKERS = (
        "403 forbidden",
        "error 403",
        "access denied",
        "request blocked",
    )
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
    CHECKER_ARTIFACT_PATHS = frozenset(
        {
            "/renderform",
            "/renderform.aspx",
            "/renderform/Form",
        }
    )
    SENSITIVE_OPAQUE_FIELD_PREFIXES = ("ff5265",)

    def parse_data(self, page: str, **kwargs) -> dict:
        """Run the complete lookup in one bounded Selenium browser session."""
        del page  # The generic HTTP response is intentionally never used.

        # This adapter has one reviewed entry point. Do not let standalone/API
        # callers redirect its privileged browser session to another origin.
        binday_url = self.BIN_DAY_URL
        postcode = kwargs.get("postcode")
        paon = kwargs.get("paon")
        web_driver = kwargs.get("web_driver")
        user_agent = kwargs.get("user_agent")
        headless = kwargs.get("headless", True)
        artifact_root = self._get_artifact_root(kwargs.get("artifact_dir"))
        deadline = monotonic() + self.TOTAL_RUN_TIMEOUT_SECONDS

        if headless is None:
            headless = True
        if not postcode:
            raise ConfigurationError("Postcode is required for South Kesteven.")
        if not paon:
            raise ConfigurationError(
                "Property number or name is required for South Kesteven."
            )
        if not str(web_driver or "").strip():
            raise ConfigurationError(
                "A remote Selenium WebDriver URL is required for South Kesteven."
            )
        web_driver = str(web_driver).strip()

        driver = None
        support = None
        stage = "create_browser"
        try:
            # create_webdriver validates websocket-client ownership before importing
            # Selenium, so a /config/websocket collision is reported safely.
            driver = create_webdriver(
                web_driver,
                headless,
                user_agent,
                __name__,
                command_timeout=min(
                    self.PAGE_LOAD_TIMEOUT_SECONDS,
                    self._remaining_seconds(deadline),
                ),
            )
            support = self._load_selenium_support()

            stage = "open_binday"
            self._set_page_load_timeout(driver, deadline)
            driver.get(binday_url)
            self._raise_if_access_denied(driver.page_source)

            stage = "resolve_checker"
            checker_url = self._wait_for_checker_url(
                self._new_wait(driver, support, deadline), support, binday_url
            )

            stage = "open_checker"
            self._set_page_load_timeout(driver, deadline)
            driver.get(checker_url)
            self._raise_if_access_denied(driver.page_source)

            stage = "enter_postcode"
            postcode_input = self._wait_for_clickable(
                self._new_wait(driver, support, deadline),
                support,
                (support.By.ID, self.POSTCODE_INPUT_ID),
                "The postcode input is missing from the South Kesteven checker.",
            )
            postcode_input.clear()
            postcode_input.send_keys(postcode)

            initial_section_id = self._get_current_section_id(driver, support)
            initial_body_markup = self._get_body_markup(driver, support)

            search_button = self._wait_for_clickable(
                self._new_wait(driver, support, deadline),
                support,
                (support.By.ID, self.SEARCH_BUTTON_ID),
                "The postcode search button is missing from the checker.",
            )
            search_button.click()
            self._raise_if_driver_access_denied(driver)

            stage = "select_address"
            address_select = self._wait_for_address_options(
                self._new_wait(driver, support, deadline), support
            )
            self._raise_if_driver_access_denied(driver)
            self._select_address(address_select, paon, support)
            self._wait_for_address_confirmation(
                self._new_wait(driver, support, deadline), support
            )
            self._raise_if_driver_access_denied(driver)

            stage = "submit_address"
            submit_button = self._wait_for_clickable(
                self._new_wait(driver, support, deadline),
                support,
                (support.By.ID, self.SUBMIT_BUTTON_ID),
                "The address submit button is missing from the checker.",
            )
            submit_button.click()
            self._raise_if_driver_access_denied(driver)
            self._wait_for_results_container(
                self._new_wait(driver, support, deadline),
                support,
                initial_section_id,
                initial_body_markup,
            )
            self._raise_if_driver_access_denied(driver)

            stage = "parse_results"
            self._remaining_seconds(deadline)
            return {"bins": self._parse_collection_rows(driver.page_source)}
        except UKBinCollectionError as exc:
            artifact_path = self._capture_debug_artifacts(
                driver,
                artifact_root,
                stage=stage,
                redactions=(str(postcode), str(paon)),
            )
            if artifact_path is not None and hasattr(exc, "add_note"):
                exc.add_note(f"Redacted debug artifacts: {artifact_path}")
            raise
        except Exception as exc:
            artifact_path = self._capture_debug_artifacts(
                driver,
                artifact_root,
                stage=stage,
                redactions=(str(postcode), str(paon)),
            )
            try:
                self._raise_if_driver_access_denied(driver)
            except UpstreamAccessDenied as translated:
                if artifact_path is not None and hasattr(translated, "add_note"):
                    translated.add_note(f"Redacted debug artifacts: {artifact_path}")
                raise translated from exc
            if support is not None and isinstance(exc, support.WebDriverException):
                translated: UKBinCollectionError = BrowserUnavailableError(
                    "The configured Selenium browser stopped responding."
                )
            else:
                translated = SiteChanged(
                    "The South Kesteven checker did not complete the expected flow."
                )
            if artifact_path is not None and hasattr(translated, "add_note"):
                translated.add_note(f"Redacted debug artifacts: {artifact_path}")
            raise translated from exc
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    _LOGGER.warning("South Kesteven WebDriver cleanup failed.")

    @staticmethod
    def _load_selenium_support() -> SimpleNamespace:
        """Import Selenium support classes only after dependency validation."""
        validate_websocket_client()
        try:
            from selenium.common.exceptions import (
                NoSuchElementException,
                TimeoutException,
                UnexpectedTagNameException,
                WebDriverException,
            )
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import Select, WebDriverWait
        except ImportError as exc:
            raise MissingDependencyError(
                "Selenium support modules are not installed completely."
            ) from exc

        return SimpleNamespace(
            By=By,
            EC=EC,
            Select=Select,
            WebDriverWait=WebDriverWait,
            NoSuchElementException=NoSuchElementException,
            TimeoutException=TimeoutException,
            UnexpectedTagNameException=UnexpectedTagNameException,
            WebDriverException=WebDriverException,
        )

    def _remaining_seconds(self, deadline: float) -> float:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise SiteChanged(
                "The South Kesteven browser flow exceeded its total timeout."
            )
        return remaining

    def _new_wait(self, driver, support, deadline: float):
        timeout = min(
            self.ELEMENT_TIMEOUT_SECONDS,
            self._remaining_seconds(deadline),
        )
        return support.WebDriverWait(driver, timeout)

    def _set_page_load_timeout(self, driver, deadline: float) -> None:
        if not hasattr(driver, "set_page_load_timeout"):
            return
        timeout = min(
            self.PAGE_LOAD_TIMEOUT_SECONDS,
            self._remaining_seconds(deadline),
        )
        driver.set_page_load_timeout(timeout)

    def _wait_for_checker_url(self, wait, support, binday_url: str) -> str:
        try:
            return wait.until(
                lambda driver: self._find_checker_url(
                    driver.page_source,
                    binday_url,
                )
            )
        except support.TimeoutException as exc:
            driver = getattr(wait, "_driver", None)
            self._raise_if_driver_access_denied(driver)
            raise SiteChanged(
                "The supported postcode checker link is missing from the binday page."
            ) from exc

    def _find_checker_url(self, html: str, binday_url: str) -> str | bool:
        if not html or not html.strip():
            return False

        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a", href=True):
            link_text = link.get_text(" ", strip=True).casefold()
            if self.CHECKER_LINK_TEXT.casefold() not in link_text:
                continue
            checker_url = urljoin(binday_url, link["href"])
            parsed = urlsplit(checker_url)
            if (
                parsed.scheme != self.CHECKER_SCHEME
                or parsed.hostname != self.CHECKER_HOST
            ):
                raise SiteChanged(
                    "The postcode checker link points outside the supported service."
                )
            return checker_url
        return False

    def _raise_if_access_denied(self, html: str) -> None:
        text = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)
        normalized = self._normalize_text(text)
        if any(marker in normalized for marker in self.ACCESS_DENIED_MARKERS):
            raise UpstreamAccessDenied(
                "South Kesteven denied browser access to the bin checker."
            )

    def _raise_if_driver_access_denied(self, driver) -> None:
        """Classify a browser denial without trusting arbitrary driver values."""
        if driver is None:
            return
        try:
            page_source = getattr(driver, "page_source", "")
        except Exception:
            return
        if not isinstance(page_source, str):
            return
        self._raise_if_access_denied(page_source)

    def _raise_if_wait_access_denied(self, wait) -> None:
        self._raise_if_driver_access_denied(getattr(wait, "_driver", None))

    def _wait_for_clickable(self, wait, support, locator, error_message):
        try:
            return wait.until(support.EC.element_to_be_clickable(locator))
        except support.TimeoutException as exc:
            self._raise_if_wait_access_denied(wait)
            raise SiteChanged(error_message) from exc

    def _wait_for_address_options(self, wait, support):
        try:
            return wait.until(
                lambda driver: self._address_options_ready(driver, support)
            )
        except support.TimeoutException as exc:
            self._raise_if_wait_access_denied(wait)
            raise SiteChanged(
                "The address dropdown did not appear after the postcode search."
            ) from exc

    def _address_options_ready(self, driver, support):
        try:
            address_select = driver.find_element(support.By.ID, self.ADDRESS_SELECT_ID)
        except support.NoSuchElementException:
            return False

        if not address_select.is_displayed():
            return False

        try:
            options = [
                option
                for option in support.Select(address_select).options
                if option.text.strip()
            ]
        except support.UnexpectedTagNameException as exc:
            raise SiteChanged(
                "The South Kesteven address control is no longer a selection list."
            ) from exc
        return address_select if options else False

    def _wait_for_address_confirmation(self, wait, support):
        try:
            return wait.until(
                lambda driver: self._address_confirmation_ready(driver, support)
            )
        except support.TimeoutException as exc:
            self._raise_if_wait_access_denied(wait)
            raise SiteChanged(
                "The selected address was not confirmed by the checker."
            ) from exc

    def _address_confirmation_ready(self, driver, support):
        try:
            address_value = driver.find_element(support.By.ID, self.ADDRESS_VALUE_ID)
            change_button = driver.find_element(support.By.ID, self.CHANGE_BUTTON_ID)
        except support.NoSuchElementException:
            return False

        selected_value = (address_value.get_attribute("value") or "").strip()
        if selected_value and change_button.is_displayed():
            return True

        try:
            display_name = driver.find_element(support.By.ID, self.ADDRESS_DISPLAY_ID)
        except support.NoSuchElementException:
            return False

        return bool((display_name.text or "").strip()) and change_button.is_displayed()

    def _wait_for_results_container(
        self,
        wait,
        support,
        initial_section_id: str | None,
        initial_body_markup: str,
    ):
        try:
            return wait.until(
                lambda driver: self._results_container_ready(
                    driver,
                    support,
                    initial_section_id,
                    initial_body_markup,
                )
            )
        except support.TimeoutException as exc:
            self._raise_if_wait_access_denied(wait)
            raise SiteChanged(
                "Collection results did not load after the address was submitted."
            ) from exc

    def _results_container_ready(
        self,
        driver,
        support,
        initial_section_id: str | None,
        initial_body_markup: str,
    ):
        try:
            body_markup = self._get_body_markup(driver, support)
        except SiteChanged:
            return False

        if not body_markup or body_markup == initial_body_markup:
            return False

        current_section_id = self._get_current_section_id(driver, support)
        section_changed = bool(
            initial_section_id
            and current_section_id
            and current_section_id != initial_section_id
        )
        address_form_gone = self.POSTCODE_INPUT_ID not in body_markup
        normalized_markup = body_markup.casefold()
        has_collection_markup = (
            "alloy-table" in normalized_markup
            or "your collections" in normalized_markup
        )
        return address_form_gone and (section_changed or has_collection_markup)

    def _select_address(self, address_select, paon: str, support) -> None:
        target = self._normalize_text(str(paon))
        try:
            select = support.Select(address_select)
        except support.UnexpectedTagNameException as exc:
            raise SiteChanged(
                "The South Kesteven address control is no longer a selection list."
            ) from exc
        matches = [
            option
            for option in select.options
            if self._address_component(option.text, target) == target
        ]

        if not matches:
            raise AddressMismatchError(
                "The configured property was not found in the address results."
            )
        if len(matches) > 1:
            raise AddressMismatchError(
                "The configured property matched more than one address."
            )
        select.select_by_visible_text(matches[0].text)

    @classmethod
    def _address_component(cls, address: str, target: str) -> str:
        normalized_address = cls._normalize_text(address)
        if re.fullmatch(r"[0-9]+[a-z]?", target):
            return re.split(r"[\s,]", normalized_address, maxsplit=1)[0]
        return normalized_address.split(",", maxsplit=1)[0].strip()

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value or "")
        return " ".join(normalized.split()).casefold()

    def _get_current_section_id(self, driver, support) -> str | None:
        try:
            return driver.find_element(
                support.By.ID, self.CURRENT_SECTION_ID
            ).get_attribute("value")
        except support.NoSuchElementException:
            return None

    def _get_body_markup(self, driver, support) -> str:
        try:
            body_content = driver.find_element(support.By.ID, self.BODY_CONTENT_ID)
        except support.NoSuchElementException as exc:
            raise SiteChanged("The checker body container is missing.") from exc
        return body_content.get_attribute("innerHTML") or ""

    @staticmethod
    def _get_artifact_root(artifact_dir: str | None) -> Path | None:
        if not artifact_dir or not str(artifact_dir).strip():
            return None
        return Path(artifact_dir)

    def _capture_debug_artifacts(
        self,
        driver,
        artifact_root: Path | None,
        *,
        stage: str,
        redactions: tuple[str, ...],
    ) -> Path | None:
        """Write opt-in HTML/metadata without screenshots or household values."""
        if driver is None or artifact_root is None:
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            artifact_path = artifact_root / f"{timestamp}-{uuid.uuid4().hex[:8]}"
            artifact_path.mkdir(parents=True, exist_ok=False)

            html = self._redact_html(
                str(getattr(driver, "page_source", "") or ""), redactions
            )

            metadata = {
                "stage": stage,
                "current_url": self._sanitize_url(
                    str(getattr(driver, "current_url", "") or "")
                ),
            }
            (artifact_path / "page.html").write_text(html, encoding="utf-8")
            (artifact_path / "metadata.json").write_text(
                json.dumps(metadata, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            return artifact_path.resolve()
        except Exception:
            _LOGGER.warning("Unable to write redacted South Kesteven debug artifacts.")
            return None

    @classmethod
    def _redact_html(cls, html: str, redactions: tuple[str, ...]) -> str:
        """Remove configured and form-derived household values from HTML.

        Form state is default-deny: values and option/display text are removed
        even when the upstream service uses opaque field names.  Selector names
        and structural markup remain available for diagnosing site drift.
        """
        redacted = html
        for value in redactions:
            if not value or value == "None":
                continue
            variants = {
                value,
                re.sub(r"\s+", "", value),
                quote(value),
                quote_plus(value),
            }
            for variant in sorted(variants, key=len, reverse=True):
                if variant:
                    redacted = re.sub(
                        re.escape(variant),
                        "[REDACTED]",
                        redacted,
                        flags=re.IGNORECASE,
                    )

        soup = BeautifulSoup(redacted, "html.parser")
        for script in soup.find_all("script"):
            script.clear()
            script.append("[REDACTED SCRIPT]")

        sensitive_markers = (
            "address",
            "displayname",
            "postcode",
            "property",
            "paon",
            "uprn",
            "usrn",
        )
        form_control_tags = {
            "button",
            "input",
            "option",
            "output",
            "select",
            "textarea",
        }
        value_attributes = {
            "aria-label",
            "aria-valuetext",
            "placeholder",
            "title",
            "value",
        }

        for field in soup.find_all(True):
            descriptor = " ".join(
                str(field.get(attribute, ""))
                for attribute in (
                    "id",
                    "name",
                    "for",
                    "aria-label",
                    "autocomplete",
                )
            ).casefold()
            field_id = str(field.get("id", "")).casefold()
            opaque_sensitive = any(
                field_id.startswith(prefix)
                for prefix in cls.SENSITIVE_OPAQUE_FIELD_PREFIXES
            )
            semantic_sensitive = any(
                marker in descriptor for marker in sensitive_markers
            )
            style = str(field.get("style", "")).casefold().replace(" ", "")
            hidden = (
                field.has_attr("hidden")
                or str(field.get("aria-hidden", "")).casefold() == "true"
                or (
                    field.name == "input"
                    and str(field.get("type", "")).casefold() == "hidden"
                )
                or "display:none" in style
                or "visibility:hidden" in style
            )
            form_control = field.name in form_control_tags

            if form_control or opaque_sensitive or semantic_sensitive or hidden:
                for attribute in list(field.attrs):
                    normalized_attribute = attribute.casefold()
                    if (
                        normalized_attribute in value_attributes
                        or normalized_attribute.startswith("data-")
                    ):
                        field[attribute] = "[REDACTED]"

            if field.name == "option":
                field.attrs.pop("selected", None)

            redact_text = (
                field.name in {"option", "output", "textarea"}
                or opaque_sensitive
                or semantic_sensitive
                or hidden
            )
            if redact_text:
                for text_node in list(field.find_all(string=True)):
                    if text_node.strip():
                        text_node.replace_with("[REDACTED]")

        redacted = str(soup)
        return re.sub(
            r"(?i)((?:uprn|usrn)[^0-9]{0,20})[0-9]{6,15}",
            r"\1[REDACTED]",
            redacted,
        )

    @classmethod
    def _sanitize_url(cls, value: str) -> str | None:
        """Retain only an allowlisted origin and a known non-identifier route."""
        if not value:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        try:
            parsed_port = parsed.port
        except ValueError:
            return None

        default_port = 443 if parsed.scheme == "https" else 80
        if parsed_port not in {None, default_port}:
            return None

        binday = urlsplit(cls.BIN_DAY_URL)
        origin = (parsed.scheme.casefold(), parsed.hostname.casefold())
        binday_origin = (binday.scheme.casefold(), (binday.hostname or "").casefold())
        checker_origin = (cls.CHECKER_SCHEME.casefold(), cls.CHECKER_HOST.casefold())

        safe_path = ""
        if origin == binday_origin:
            if parsed.path == binday.path:
                safe_path = binday.path
        elif origin == checker_origin:
            if parsed.path in cls.CHECKER_ARTIFACT_PATHS:
                safe_path = parsed.path
        else:
            return None

        host = parsed.hostname
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return urlunsplit((parsed.scheme.casefold(), host, safe_path, "", ""))

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
            raise SiteChanged(
                "No collection rows were found on the South Kesteven results page."
            )
        return bins
