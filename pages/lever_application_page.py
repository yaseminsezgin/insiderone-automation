"""Lever Application Form — https://jobs.lever.co/insiderone/<posting-id>/apply"""

from selenium.webdriver.common.by import By

from config import settings
from pages.base_page import BasePage


class LeverApplicationPage(BasePage):
    """Step 6: the application form the Apply button must lead to."""

    APPLY_URL_PART = "/apply"

    # --- locators -----------------------------------------------------------
    # The board's Apply button lands on the posting page, which carries this CTA.
    SHOW_PAGE_APPLY_BUTTON = (By.CSS_SELECTOR, "a[data-qa='show-page-apply']")
    APPLICATION_FORM = (By.CSS_SELECTOR, "form#application-form")
    SUBMIT_APPLICATION_HEADING = (
        By.XPATH,
        "//form[@id='application-form']//h4[normalize-space()='Submit your application']",
    )
    FULL_NAME_INPUT = (By.CSS_SELECTOR, "form#application-form input[data-qa='name-input']")
    EMAIL_INPUT = (By.CSS_SELECTOR, "form#application-form input[data-qa='email-input']")
    # The file input itself is hidden by design; the visible affordance is the anchor.
    RESUME_INPUT = (By.CSS_SELECTOR, "form#application-form input[name='resume'][type='file']")
    RESUME_UPLOAD_BUTTON = (By.CSS_SELECTOR, "form#application-form a.visible-resume-upload")
    SUBMIT_BUTTON = (By.CSS_SELECTOR, "form#application-form [data-qa='btn-submit']")
    POSTING_HEADLINE = (By.CSS_SELECTOR, ".posting-headline h2, .posting-header h2")

    # --- page state ---------------------------------------------------------
    def wait_until_loaded(self) -> "LeverApplicationPage":
        """Ensure we end up on the form, following the posting page's CTA if needed."""
        self.wait_for_url_contains(settings.LEVER_URL_PART)

        if self.APPLY_URL_PART not in self.current_url:
            self.log.info("Landed on the posting page; following 'Apply for this job'")
            self.click(self.SHOW_PAGE_APPLY_BUTTON)
            self.wait_for_url_contains(self.APPLY_URL_PART)

        self.find_visible(self.APPLICATION_FORM)
        self.log.info("Lever application form loaded: %s", self.current_url)
        return self

    # --- verifications ------------------------------------------------------
    def is_application_form_displayed(self) -> bool:
        return (
            self.is_on_lever_domain()
            and self.APPLY_URL_PART in self.current_url
            and self.is_visible(self.APPLICATION_FORM)
            and self.is_visible(self.SUBMIT_APPLICATION_HEADING)
        )

    def is_on_lever_domain(self) -> bool:
        return settings.LEVER_URL_PART in self.current_url

    def are_required_fields_displayed(self) -> bool:
        """Name and email are rendered inputs; the resume field is a hidden file input."""
        visible_fields = all(
            self.is_visible(locator)
            for locator in (self.FULL_NAME_INPUT, self.EMAIL_INPUT, self.RESUME_UPLOAD_BUTTON)
        )
        return visible_fields and self.is_resume_input_present()

    def is_resume_input_present(self) -> bool:
        return bool(self.driver.find_elements(*self.RESUME_INPUT))

    def is_submit_button_displayed(self) -> bool:
        return self.is_visible(self.SUBMIT_BUTTON)

    def posting_title(self) -> str:
        return self.text_of(self.POSTING_HEADLINE)
