"""WebDriver creation, parameterised by browser name.

Driver binaries are resolved automatically by Selenium Manager (Selenium >= 4.6),
so no manual chromedriver/geckodriver installation is required.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from config import settings

SUPPORTED_BROWSERS = ("chrome", "firefox")


def _chrome_options(headless: bool) -> ChromeOptions:
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument(f"--window-size={settings.WINDOW_SIZE[0]},{settings.WINDOW_SIZE[1]}")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=en-US")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.set_capability("pageLoadStrategy", "eager")
    return options


def _firefox_options(headless: bool) -> FirefoxOptions:
    options = FirefoxOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument(f"--width={settings.WINDOW_SIZE[0]}")
    options.add_argument(f"--height={settings.WINDOW_SIZE[1]}")
    options.set_preference("intl.accept_languages", "en-US, en")
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_capability("pageLoadStrategy", "eager")
    return options


def create_driver(browser: str = settings.DEFAULT_BROWSER, headless: bool = settings.HEADLESS):
    """Return a configured WebDriver for `browser` ("chrome" or "firefox")."""
    browser = (browser or "").lower().strip()
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError(
            f"Unsupported browser: {browser!r}. Supported browsers: {', '.join(SUPPORTED_BROWSERS)}"
        )

    if browser == "chrome":
        driver = webdriver.Chrome(options=_chrome_options(headless))
    else:
        driver = webdriver.Firefox(options=_firefox_options(headless))

    driver.set_page_load_timeout(settings.PAGE_LOAD_TIMEOUT)
    if not headless:
        driver.maximize_window()
    return driver
