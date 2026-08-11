"""End-to-end scenario: Insider One home page -> Career page -> job list -> Lever form.

Each test method is one numbered step of the scenario. The class shares a single
browser session and is marked `incremental`, so a failing step stops the flow
instead of reporting misleading follow-up failures.
"""

import pytest

from config import settings
from pages.home_page import HomePage
from pages.open_positions_page import OpenPositionsPage


@pytest.mark.incremental
@pytest.mark.usefixtures("driver")
class TestInsiderOneCareerFlow:
    """Steps 1-6 of the Insider One career scenario."""

    # Handed between steps through the shared browser session.
    careers_page = None
    open_positions_page = None
    listed_jobs: list = []

    # --- Step 1 -------------------------------------------------------------
    def test_01_home_page_is_opened(self):
        """Visit insiderone.com and verify we are on the Insider One home page."""
        home_page = HomePage(self.driver).open_home_page()

        assert home_page.is_on_home_url(), (
            f"Expected the Insider One home page, but the URL is {home_page.current_url!r}"
        )
        assert home_page.EXPECTED_TITLE in home_page.title, (
            f"Unexpected page title: {home_page.title!r}"
        )
        assert home_page.is_home_page_displayed(), "The Insider One home page did not render"
        assert home_page.is_we_are_hiring_link_displayed(), (
            "The \"We're hiring\" link is not present on the home page"
        )

        type(self).home_page = home_page

    # --- Step 2 -------------------------------------------------------------
    def test_02_we_are_hiring_opens_career_page_with_explore_button(self):
        """Click "We're hiring" and verify the Career page and its CTA."""
        careers_page = self.home_page.click_we_are_hiring()

        assert settings.CAREERS_URL_PART in careers_page.current_url, (
            f"Expected a /careers URL, got {careers_page.current_url!r}"
        )
        assert careers_page.is_careers_page_displayed(), (
            f"The Career page did not render (title={careers_page.title!r}, "
            f"url={careers_page.current_url!r})"
        )
        assert careers_page.is_explore_open_roles_button_displayed(), (
            "The 'Explore open roles' button was not found on the Career page"
        )

        type(self).careers_page = careers_page

    # --- Step 3 -------------------------------------------------------------
    def test_03_explore_open_roles_opens_department_positions(self):
        """Click 'Explore open roles', then the department block's open positions."""
        careers_page = self.careers_page
        careers_page.click_explore_open_roles()

        assert careers_page.is_open_roles_section_displayed(), (
            "'Explore open roles' did not reveal the open roles section"
        )
        assert careers_page.is_department_block_displayed(settings.DEPARTMENT_BLOCK), (
            f"The {settings.DEPARTMENT_BLOCK!r} block was not found. "
            f"Blocks on the page: {careers_page.department_names()}"
        )

        label = careers_page.open_positions_label(settings.DEPARTMENT_BLOCK)
        assert "Open Position" in label, (
            f"Expected an 'xx Open Positions' link in the {settings.DEPARTMENT_BLOCK!r} block, "
            f"found {label!r}"
        )

        open_positions_page = careers_page.click_open_positions_of(settings.DEPARTMENT_BLOCK)

        assert open_positions_page.is_open_positions_page_displayed(), (
            f"The open positions page did not open (url={open_positions_page.current_url!r})"
        )

        type(self).open_positions_page = open_positions_page

    # --- Step 4 -------------------------------------------------------------
    def test_04_location_and_team_filters_show_the_job_list(self):
        """Apply the configured Location and Team filters and verify the list shows up."""
        open_positions_page = self.open_positions_page
        open_positions_page.filter_by_location(settings.FILTER_LOCATION)
        open_positions_page.filter_by_team(settings.FILTER_TEAM)

        assert (
            open_positions_page.selected_filter_value(OpenPositionsPage.LOCATION_FILTER)
            == settings.FILTER_LOCATION
        ), "The Location filter does not hold the selected value"
        assert (
            open_positions_page.selected_filter_value(OpenPositionsPage.TEAM_FILTER)
            == settings.FILTER_TEAM
        ), "The Team filter does not hold the selected value"
        assert open_positions_page.is_job_list_displayed(), (
            f"No job was listed for Location={settings.FILTER_LOCATION!r} and "
            f"Team={settings.FILTER_TEAM!r}"
        )

    # --- Step 5 -------------------------------------------------------------
    def test_05_every_listed_job_matches_the_filters(self):
        """Every listed job must belong to the filtered team and location."""
        jobs = self.open_positions_page.get_job_postings()
        assert jobs, "The filtered job list is empty, so there is nothing to verify"

        mismatched_team = [job for job in jobs if not job.has_team(settings.FILTER_TEAM)]
        mismatched_location = [
            job for job in jobs if not job.has_location(settings.FILTER_LOCATION)
        ]

        assert not mismatched_team, (
            f"These jobs do not contain {settings.FILTER_TEAM!r} in their position information: "
            + "; ".join(str(job) for job in mismatched_team)
        )
        assert not mismatched_location, (
            f"These jobs do not contain {settings.FILTER_LOCATION!r} in their location: "
            + "; ".join(str(job) for job in mismatched_location)
        )

        type(self).listed_jobs = jobs

    # --- Step 6 -------------------------------------------------------------
    def test_06_apply_button_redirects_to_lever_application_form(self):
        """The Apply button must lead to the Lever application form."""
        application_page = self.open_positions_page.click_apply(index=0)

        assert application_page.is_on_lever_domain(), (
            f"Apply did not redirect to Lever (url={application_page.current_url!r})"
        )
        assert application_page.is_application_form_displayed(), (
            f"The Lever application form did not open (url={application_page.current_url!r})"
        )
        assert application_page.are_required_fields_displayed(), (
            "The Lever application form is missing its name/email/resume fields"
        )
        assert application_page.is_submit_button_displayed(), (
            "The Lever application form has no submit button"
        )
