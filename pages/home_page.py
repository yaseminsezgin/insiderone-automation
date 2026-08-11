"""Insider One home page — https://insiderone.com/"""

from selenium.webdriver.common.by import By

from config import settings
from pages.base_page import BasePage
from pages.careers_page import CareersPage


class HomePage(BasePage):
    """Step 1 & 2: verify the home page and follow the "We're hiring" link."""

    URL = settings.BASE_URL
    EXPECTED_TITLE = "Insider One | #1 Platform for AI-Powered Customer Engagement"

    # --- locators -----------------------------------------------------------
    COOKIE_ACCEPT_BUTTON = (By.CSS_SELECTOR, "#cookie-law-info-bar .wt-cli-accept-all-btn")
    HEADER = (By.CSS_SELECTOR, "header.header-insiderone")
    HEADER_LOGO = (By.CSS_SELECTOR, "header.header-insiderone .header-logo")
    HERO_HEADING = (By.CSS_SELECTOR, "main h1, h1")
    # The only "hiring" link on the page lives in the footer COMPANY column.
    WE_ARE_HIRING_LINK = (
        By.XPATH,
        "//footer//a[@href='/careers/'][contains(normalize-space(.), 'hiring')]",
    )

    # --- actions ------------------------------------------------------------
    def open_home_page(self) -> "HomePage":
        self.open(self.URL)
        self.accept_cookies()
        return self

    def accept_cookies(self) -> None:
        """Dismiss the consent bar so it cannot intercept later clicks."""
        if self.is_visible(self.COOKIE_ACCEPT_BUTTON, timeout=settings.SHORT_WAIT):
            self.click(self.COOKIE_ACCEPT_BUTTON)
            self.log.info("Cookie consent accepted")

    def click_we_are_hiring(self) -> CareersPage:
        link = self.find(self.WE_ARE_HIRING_LINK)
        self.log.info("Clicking footer link: %r", self.element_text(link))
        self.click_element(link)
        careers_page = CareersPage(self.driver, self.timeout)
        careers_page.wait_until_loaded()
        return careers_page

    # --- verifications ------------------------------------------------------
    def is_home_page_displayed(self) -> bool:
        """True only when URL, title and the home-page chrome all line up."""
        return (
            self.is_on_home_url()
            and self.EXPECTED_TITLE in self.title
            and self.is_visible(self.HEADER)
            and self.is_visible(self.HEADER_LOGO)
        )

    def is_on_home_url(self) -> bool:
        """The home page is the site root (useinsider.com redirects to insiderone.com)."""
        url = self.current_url.split("?")[0].rstrip("/")
        return url in ("https://insiderone.com", "https://useinsider.com", "http://insiderone.com")

    def is_we_are_hiring_link_displayed(self) -> bool:
        return self.is_visible(self.WE_ARE_HIRING_LINK)

    def hero_heading_text(self) -> str:
        return self.text_of(self.HERO_HEADING)
