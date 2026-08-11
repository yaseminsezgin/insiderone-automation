"""Pytest fixtures: parameterised browser, failure screenshots, ordered steps."""

import pytest

from config import settings
from utils.driver_factory import SUPPORTED_BROWSERS, create_driver
from utils.logger import get_logger
from utils.screenshot import take_screenshot

log = get_logger("conftest")


# --- CLI options ------------------------------------------------------------
def pytest_addoption(parser):
    parser.addoption(
        "--browser",
        action="store",
        default=settings.DEFAULT_BROWSER,
        choices=list(SUPPORTED_BROWSERS),
        help="Browser to run the tests against (chrome or firefox).",
    )
    parser.addoption(
        "--headless",
        action="store_true",
        default=settings.HEADLESS,
        help="Run the selected browser in headless mode.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "incremental: abort the remaining steps of a class once one step fails"
    )


# --- driver fixture ---------------------------------------------------------
@pytest.fixture(scope="class")
def browser_name(request) -> str:
    return request.config.getoption("--browser")


@pytest.fixture(scope="class")
def driver(request, browser_name):
    """One browser session per test class, so the scenario runs as a single flow."""
    headless = request.config.getoption("--headless")
    log.info("Starting %s (headless=%s)", browser_name, headless)

    web_driver = create_driver(browser=browser_name, headless=headless)
    web_driver.delete_all_cookies()
    request.cls.driver = web_driver

    yield web_driver

    log.info("Quitting %s", browser_name)
    web_driver.quit()


# --- reporting: screenshot on failure + incremental steps -------------------
@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when not in ("setup", "call") or not report.failed:
        return

    web_driver = item.funcargs.get("driver")
    path = take_screenshot(web_driver, item.name)
    if path:
        report.sections.append(("Screenshot", path))

    if "incremental" in item.keywords and item.cls is not None:
        item.cls._failed_incremental_step = item.name


def pytest_runtest_setup(item):
    """Skip the remaining steps of an incremental class after the first failure."""
    if "incremental" not in item.keywords or item.cls is None:
        return
    failed_step = getattr(item.cls, "_failed_incremental_step", None)
    if failed_step is not None:
        pytest.skip(f"Previous step failed: {failed_step}")
