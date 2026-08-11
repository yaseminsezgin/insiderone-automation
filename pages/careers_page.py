"""Insider One Career page — https://insiderone.com/careers/

Hosts both the "Explore open roles" CTA (step 2) and the department cards whose
"xx Open Positions" links lead to the Lever job board (step 3).
"""

import re

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from pages.base_page import BasePage
from pages.open_positions_page import OpenPositionsPage


class CareersPage(BasePage):
    """Step 2 & 3: verify the Career page and open a department's positions."""

    URL = f"{settings.BASE_URL.rstrip('/')}/careers/"
    EXPECTED_TITLE = "Insider One Careers"

    # --- locators -----------------------------------------------------------
    COOKIE_ACCEPT_BUTTON = (By.CSS_SELECTOR, "#cookie-law-info-bar .wt-cli-accept-all-btn")
    PAGE_HEADING = (By.CSS_SELECTOR, ".insiderone-hero-banner-content-heading")
    EXPLORE_OPEN_ROLES_BUTTON = (
        By.XPATH,
        "//a[contains(@class,'inso-btn')][@href='#open-roles']"
        "[.//span[normalize-space()='Explore open roles']]",
    )
    OPEN_ROLES_SECTION = (By.ID, "open-roles")
    OPEN_ROLES_SECTION_HEADING = (
        By.XPATH,
        "//*[@id='open-roles']//h2[normalize-space()='Explore open roles']",
    )
    DEPARTMENT_CARDS = (By.CSS_SELECTOR, "#open-roles .insiderone-icon-cards-grid-item")
    SEE_ALL_TEAMS_BUTTON = (By.CSS_SELECTOR, "#open-roles .see-more")

    # Career page "proof" blocks used by the page verification.
    LOCATIONS_SECTION = (By.CSS_SELECTOR, ".insiderone-locations-slider-item-title")

    @staticmethod
    def _department_card(department: str) -> tuple[str, str]:
        return (
            By.CSS_SELECTOR,
            f"#open-roles .insiderone-icon-cards-grid-item[data-department='{department}']",
        )

    @staticmethod
    def _open_positions_link(department: str) -> tuple[str, str]:
        return (
            By.CSS_SELECTOR,
            f"#open-roles .insiderone-icon-cards-grid-item[data-department='{department}']"
            " a.insiderone-icon-cards-grid-item-btn",
        )

    # --- actions ------------------------------------------------------------
    def open_careers_page(self) -> "CareersPage":
        self.open(self.URL)
        if self.is_visible(self.COOKIE_ACCEPT_BUTTON, timeout=settings.SHORT_WAIT):
            self.click(self.COOKIE_ACCEPT_BUTTON)
        return self.wait_until_loaded()

    def wait_until_loaded(self) -> "CareersPage":
        self.wait_for_url_contains(settings.CAREERS_URL_PART)
        self.find_visible(self.PAGE_HEADING)
        return self

    def click_explore_open_roles(self) -> "CareersPage":
        """Click the CTA; it scrolls the page to the #open-roles section."""
        self.click(self.EXPLORE_OPEN_ROLES_BUTTON)
        self.find_visible(self.OPEN_ROLES_SECTION_HEADING)
        self.log.info("Open roles section is in view")
        return self

    EXPAND_ATTEMPTS = 3

    def expand_all_teams(self) -> bool:
        """Reveal the collapsed department cards, verifying the toggle really opened.

        Only part of the departments sit in the always-visible grid; the rest live
        behind a "See all teams" toggle. Clicking it can be swallowed while the page
        is still settling, so the opened state is confirmed rather than assumed.
        """
        if not self.is_visible(self.SEE_ALL_TEAMS_BUTTON, timeout=settings.SHORT_WAIT):
            return False

        for attempt in range(1, self.EXPAND_ATTEMPTS + 1):
            toggle = self.find(self.SEE_ALL_TEAMS_BUTTON)
            if toggle.get_attribute("aria-expanded") == "true":
                return True

            self.click_element(toggle)
            try:
                WebDriverWait(self.driver, settings.SHORT_WAIT).until(
                    lambda d: d.find_element(*self.SEE_ALL_TEAMS_BUTTON).get_attribute(
                        "aria-expanded"
                    )
                    == "true"
                )
                self.log.info("Expanded the collapsed department cards")
                return True
            except TimeoutException:
                self.log.info(
                    "The 'See all teams' toggle did not open (attempt %s/%s)",
                    attempt,
                    self.EXPAND_ATTEMPTS,
                )

        self.log.warning("The collapsed department cards stayed hidden")
        return False

    def click_open_positions_of(self, department: str) -> OpenPositionsPage:
        """Click "xx Open Positions" inside `department`'s card and follow it."""
        link = self.wait_for_open_positions_link(department)
        label = self.element_text(link)
        target = link.get_attribute("href")
        self.log.info("Clicking %r in the %r block (href=%s)", label, department, target)

        handles_before = self.window_handles()
        self.click_element(link)

        if not self.switch_to_new_window(handles_before, timeout=settings.SHORT_WAIT):
            self.wait_for_url_contains("lever.co")

        open_positions_page = OpenPositionsPage(self.driver, self.timeout)
        open_positions_page.wait_until_loaded()
        return open_positions_page

    # Values the CMS ships before the widget script rewrites the link.
    PLACEHOLDER_HREFS = ("", "#")

    def wait_for_open_positions_link(self, department: str):
        """Return the card link once its href has been resolved by the widget script.

        The markup ships with `href="#"` and the widget rewrites it only after the
        Lever API responds. The raw DOM attribute is read on purpose: `get_attribute`
        resolves "#" into an absolute page URL, which would hide the placeholder.
        """
        locator = self._open_positions_link(department)
        self.find(self._department_card(department))
        try:
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: (d.find_element(*locator).get_dom_attribute("href") or "").strip()
                not in self.PLACEHOLDER_HREFS
            )
        except TimeoutException:
            self.log.warning("Open positions link for %r still points at a placeholder", department)
        return self.find_visible(locator)

    # --- verifications ------------------------------------------------------
    def is_careers_page_displayed(self) -> bool:
        return (
            settings.CAREERS_URL_PART in self.current_url
            and self.EXPECTED_TITLE in self.title
            and self.is_visible(self.PAGE_HEADING)
        )

    def is_explore_open_roles_button_displayed(self) -> bool:
        return self.is_visible(self.EXPLORE_OPEN_ROLES_BUTTON)

    def is_open_roles_section_displayed(self) -> bool:
        return self.is_visible(self.OPEN_ROLES_SECTION_HEADING)

    def is_department_block_displayed(self, department: str) -> bool:
        self.expand_all_teams()
        return self.is_visible(self._department_card(department))

    def department_names(self) -> list[str]:
        return [
            card.get_attribute("data-department")
            for card in self.find_all(self.DEPARTMENT_CARDS)
        ]

    def open_positions_label(self, department: str) -> str:
        """The card CTA text, e.g. "12 Open Positions"."""
        return self.element_text(self.wait_for_open_positions_link(department))

    def open_positions_count(self, department: str) -> int | None:
        """Leading number of the "xx Open Positions" label, None when absent."""
        match = re.search(r"(\d+)", self.open_positions_label(department))
        return int(match.group(1)) if match else None
