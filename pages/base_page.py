"""Base class for every page object: waits, safe interactions, window handling."""

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from utils.logger import get_logger


class BasePage:
    """Common Selenium plumbing shared by all page objects."""

    def __init__(self, driver, timeout: int = settings.EXPLICIT_WAIT):
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)
        self.log = get_logger(type(self).__name__)

    # --- navigation ---------------------------------------------------------
    def open(self, url: str) -> "BasePage":
        self.log.info("Navigating to %s", url)
        self.driver.get(url)
        self.wait_for_document_ready()
        return self

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    @property
    def title(self) -> str:
        return self.driver.title

    def wait_for_document_ready(self) -> None:
        try:
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
            )
        except TimeoutException:
            self.log.warning("document.readyState did not settle within %ss", self.timeout)

    def wait_for_url_contains(self, fragment: str, timeout: int | None = None) -> bool:
        try:
            WebDriverWait(self.driver, timeout or self.timeout).until(EC.url_contains(fragment))
            return True
        except TimeoutException:
            return False

    # --- element lookups ----------------------------------------------------
    def find(self, locator: tuple[str, str], timeout: int | None = None) -> WebElement:
        """Wait until the element is present in the DOM and return it."""
        return WebDriverWait(self.driver, timeout or self.timeout).until(
            EC.presence_of_element_located(locator),
            message=f"Element not present: {locator}",
        )

    def find_visible(self, locator: tuple[str, str], timeout: int | None = None) -> WebElement:
        return WebDriverWait(self.driver, timeout or self.timeout).until(
            EC.visibility_of_element_located(locator),
            message=f"Element not visible: {locator}",
        )

    def find_all(self, locator: tuple[str, str], timeout: int | None = None) -> list[WebElement]:
        """Wait until at least one element is visible and return every match."""
        WebDriverWait(self.driver, timeout or self.timeout).until(
            EC.visibility_of_element_located(locator),
            message=f"No visible element for: {locator}",
        )
        return self.driver.find_elements(*locator)

    def find_clickable(self, locator: tuple[str, str], timeout: int | None = None) -> WebElement:
        return WebDriverWait(self.driver, timeout or self.timeout).until(
            EC.element_to_be_clickable(locator),
            message=f"Element not clickable: {locator}",
        )

    def is_visible(self, locator: tuple[str, str], timeout: int | None = None) -> bool:
        """Non-throwing probe used by the `verify_*` assertions."""
        try:
            self.find_visible(locator, timeout if timeout is not None else settings.SHORT_WAIT)
            return True
        except TimeoutException:
            return False

    def first_visible(
        self, locators: list[tuple[str, str]], timeout: int | None = None
    ) -> WebElement | None:
        """Return the first element that becomes visible among alternative locators.

        Marketing pages change markup often; alternatives keep the test resilient
        without weakening the assertion that follows.
        """
        deadline = timeout if timeout is not None else settings.SHORT_WAIT
        for locator in locators:
            try:
                return self.find_visible(locator, deadline)
            except TimeoutException:
                continue
        return None

    # --- interactions -------------------------------------------------------
    def scroll_into_view(self, element: WebElement) -> WebElement:
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element
        )
        return element

    def click(self, locator: tuple[str, str], timeout: int | None = None) -> WebElement:
        element = self.find_clickable(locator, timeout)
        return self.click_element(element)

    def click_element(self, element: WebElement) -> WebElement:
        """Click, falling back to a JS click when an overlay swallows the event."""
        self.scroll_into_view(element)
        try:
            element.click()
        except (
            ElementClickInterceptedException,
            ElementNotInteractableException,
            StaleElementReferenceException,
        ):
            self.log.info("Native click blocked, falling back to JS click")
            self.driver.execute_script("arguments[0].click();", element)
        return element

    def text_of(self, locator: tuple[str, str], timeout: int | None = None) -> str:
        return self.find_visible(locator, timeout).text.strip()

    @staticmethod
    def element_text(element: WebElement) -> str:
        return (element.text or "").strip()

    # --- windows / tabs -----------------------------------------------------
    def window_handles(self) -> list[str]:
        return self.driver.window_handles

    def switch_to_new_window(self, known_handles: list[str], timeout: int | None = None) -> bool:
        """Switch to a tab opened after `known_handles` was captured."""
        try:
            WebDriverWait(self.driver, timeout or self.timeout).until(
                EC.new_window_is_opened(known_handles)
            )
        except TimeoutException:
            self.log.info("No new tab was opened; staying in the current one")
            return False

        new_handle = [h for h in self.driver.window_handles if h not in known_handles][-1]
        self.driver.switch_to.window(new_handle)
        self.wait_for_document_ready()
        self.log.info("Switched to new tab: %s", self.driver.current_url)
        return True
