"""Lever job board — https://jobs.lever.co/insiderone

Reached from the Career page's "xx Open Positions" card link. Hosts the Location
and Team filters (step 4), the job list (step 5) and the Apply buttons (step 6).
"""

from dataclasses import dataclass

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from pages.base_page import BasePage
from pages.lever_application_page import LeverApplicationPage
from utils.xpath import xpath_literal


@dataclass(frozen=True)
class JobPosting:
    """Read-only snapshot of a single job card.

    The board uppercases the team and location labels with CSS, so the values read
    from the DOM are the rendered ones. Matching is therefore case-insensitive.
    """

    title: str
    team: str
    location: str
    apply_url: str

    def has_team(self, expected: str) -> bool:
        return expected.casefold() in self.team.casefold()

    def has_location(self, expected: str) -> bool:
        return expected.casefold() in self.location.casefold()

    def __str__(self) -> str:
        return f"{self.title!r} | team={self.team!r} | location={self.location!r}"


class FilterOptionNotAvailableError(AssertionError):
    """Raised when the board does not offer the requested filter value."""


class OpenPositionsPage(BasePage):
    """Step 4, 5 & 6: filter the board, read the list, start an application."""

    LOCATION_FILTER = "Location"
    TEAM_FILTER = "Team"

    # --- locators -----------------------------------------------------------
    FILTER_BAR = (By.CSS_SELECTOR, ".filter-bar")
    POSTINGS_WRAPPER = (By.CSS_SELECTOR, ".postings-wrapper")
    JOB_CARDS = (By.CSS_SELECTOR, ".posting[data-qa-posting-id]")
    JOB_TITLE = (By.CSS_SELECTOR, "[data-qa='posting-name']")
    JOB_LOCATION = (By.CSS_SELECTOR, ".posting-categories .location")
    JOB_APPLY_BUTTON = (By.CSS_SELECTOR, ".posting-apply a.posting-btn-submit")
    JOB_TEAM = (
        By.XPATH,
        "./ancestor::div[contains(@class,'postings-group')][1]"
        "//div[contains(@class,'posting-category-title')]",
    )

    @staticmethod
    def _filter_button(filter_name: str) -> tuple[str, str]:
        return (
            By.XPATH,
            f"//div[contains(@class,'filter-bar')]//div[@role='button']"
            f"[starts-with(@aria-label, 'Filter by {filter_name}:')]",
        )

    @staticmethod
    def _filter_option(filter_name: str, value: str) -> tuple[str, str]:
        return (
            By.XPATH,
            f"//div[contains(@class,'filter-bar')]//div[@role='button']"
            f"[starts-with(@aria-label, 'Filter by {filter_name}:')]"
            f"//div[contains(@class,'filter-popup')]"
            f"//a[contains(@class,'category-link')][normalize-space()={xpath_literal(value)}]",
        )

    @staticmethod
    def _filter_options(filter_name: str) -> tuple[str, str]:
        return (
            By.XPATH,
            f"//div[contains(@class,'filter-bar')]//div[@role='button']"
            f"[starts-with(@aria-label, 'Filter by {filter_name}:')]"
            f"//div[contains(@class,'filter-popup')]//a[contains(@class,'category-link')]",
        )

    # --- page state ---------------------------------------------------------
    def wait_until_loaded(self) -> "OpenPositionsPage":
        self.wait_for_url_contains("jobs.lever.co")
        self.find_visible(self.FILTER_BAR)
        self.find(self.POSTINGS_WRAPPER)
        self.log.info("Job board loaded: %s", self.current_url)
        return self

    def is_open_positions_page_displayed(self) -> bool:
        return "jobs.lever.co" in self.current_url and self.is_visible(self.FILTER_BAR)

    # --- filtering ----------------------------------------------------------
    def filter_by_location(self, location: str) -> "OpenPositionsPage":
        return self._apply_filter(self.LOCATION_FILTER, location)

    def filter_by_team(self, team: str) -> "OpenPositionsPage":
        return self._apply_filter(self.TEAM_FILTER, team)

    def _apply_filter(self, filter_name: str, value: str) -> "OpenPositionsPage":
        """Open the filter dropdown and select `value`, then wait for the reload."""
        self.log.info("Setting the %s filter to %r", filter_name, value)
        self._open_filter_dropdown(filter_name)

        try:
            option = self.find_clickable(self._filter_option(filter_name, value))
        except TimeoutException:
            available = self.available_filter_options(filter_name)
            raise FilterOptionNotAvailableError(
                f"The {filter_name} filter does not offer {value!r}. "
                f"Available options: {available}"
            ) from None

        wrapper = self.find(self.FILTER_BAR)
        self.click_element(option)

        # Selecting an option reloads the board through a query-string navigation.
        try:
            WebDriverWait(self.driver, self.timeout).until(EC.staleness_of(wrapper))
        except TimeoutException:
            self.log.info("Board updated without a full reload")

        self.wait_until_loaded()
        self._wait_for_selected_filter(filter_name, value)
        return self

    OPEN_DROPDOWN_ATTEMPTS = 3

    def _open_filter_dropdown(self, filter_name: str) -> bool:
        """Open the dropdown, retrying while the board is still binding its handlers.

        Right after a filter reload the button is present before its click handler is
        attached, so the first click can be swallowed silently.
        """
        locator = self._filter_button(filter_name)
        for attempt in range(1, self.OPEN_DROPDOWN_ATTEMPTS + 1):
            button = self.find_clickable(locator)
            if button.get_attribute("aria-expanded") == "true":
                return True

            self.click_element(button)
            try:
                WebDriverWait(self.driver, settings.SHORT_WAIT).until(
                    lambda d: d.find_element(*locator).get_attribute("aria-expanded") == "true"
                )
                return True
            except TimeoutException:
                self.log.info(
                    "The %s dropdown did not open (attempt %s/%s)",
                    filter_name,
                    attempt,
                    self.OPEN_DROPDOWN_ATTEMPTS,
                )

        self.log.warning("The %s dropdown stayed closed", filter_name)
        return False

    def _wait_for_selected_filter(self, filter_name: str, value: str) -> None:
        expected = f"Filter by {filter_name}: {value}"
        WebDriverWait(self.driver, self.timeout).until(
            lambda d: d.find_element(*self._filter_button(filter_name)).get_attribute("aria-label")
            == expected,
            message=f"The {filter_name} filter was not applied (expected aria-label {expected!r})",
        )
        self.log.info("%s filter applied: %s", filter_name, value)

    def selected_filter_value(self, filter_name: str) -> str:
        aria_label = self.find(self._filter_button(filter_name)).get_attribute("aria-label") or ""
        return aria_label.split(":", 1)[-1].strip()

    def available_filter_options(self, filter_name: str) -> list[str]:
        """Every value the dropdown offers, readable even while the popup is closed."""
        options = self.driver.find_elements(*self._filter_options(filter_name))
        texts = ((option.get_attribute("textContent") or "").strip() for option in options)
        return [text for text in texts if text and text != "All"]

    # --- job list -----------------------------------------------------------
    def is_job_list_displayed(self) -> bool:
        return self.job_count() > 0

    def job_count(self) -> int:
        return len(self.driver.find_elements(*self.JOB_CARDS))

    def _job_elements(self) -> list[WebElement]:
        return self.find_all(self.JOB_CARDS)

    def _read_job(self, card: WebElement) -> JobPosting:
        return JobPosting(
            title=self.element_text(card.find_element(*self.JOB_TITLE)),
            team=self.element_text(card.find_element(*self.JOB_TEAM)),
            location=self.element_text(card.find_element(*self.JOB_LOCATION)),
            apply_url=card.find_element(*self.JOB_APPLY_BUTTON).get_attribute("href") or "",
        )

    def get_job_postings(self) -> list[JobPosting]:
        """Snapshot every listed job so assertions run against stable data."""
        postings = [self._read_job(card) for card in self._job_elements()]
        for posting in postings:
            self.log.info("Listed job -> %s", posting)
        return postings

    # --- apply --------------------------------------------------------------
    def click_apply(self, index: int = 0) -> LeverApplicationPage:
        """Click the Apply button of the job at `index` and reach the application form."""
        cards = self._job_elements()
        if index >= len(cards):
            raise AssertionError(f"No job at index {index}; the board lists {len(cards)} job(s)")

        card = cards[index]
        title = self.element_text(card.find_element(*self.JOB_TITLE))
        self.log.info("Clicking Apply for %r", title)

        handles_before = self.window_handles()
        self.click_element(card.find_element(*self.JOB_APPLY_BUTTON))
        self.switch_to_new_window(handles_before, timeout=settings.SHORT_WAIT)

        application_page = LeverApplicationPage(self.driver, self.timeout)
        application_page.wait_until_loaded()
        return application_page
