"""Centralised, environment-overridable test configuration."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = PROJECT_ROOT / "reports" / "screenshots"

# --- Application under test -------------------------------------------------
BASE_URL = os.getenv("BASE_URL", "https://useinsider.com/")

# URL fragments used by the page verifications.
CAREERS_URL_PART = "/careers"
OPEN_POSITIONS_URL_PART = "open-positions"
LEVER_URL_PART = "lever.co"

# --- Test data --------------------------------------------------------------
# The department block stays the one from the scenario; its card sits in the
# always-visible grid and links to the unfiltered board, which is where the
# Location/Team filters below are applied. Overridable so the suite can follow the
# board when its open roles change.
DEPARTMENT_BLOCK = os.getenv("DEPARTMENT_BLOCK", "Software Development")
FILTER_LOCATION = os.getenv("FILTER_LOCATION", "Istanbul, Turkiye")
FILTER_TEAM = os.getenv("FILTER_TEAM", "Customer Success")

# --- Runtime ----------------------------------------------------------------
DEFAULT_BROWSER = os.getenv("BROWSER", "chrome").lower()
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("1", "true", "yes")
WINDOW_SIZE = (1920, 1080)

EXPLICIT_WAIT = int(os.getenv("EXPLICIT_WAIT", "20"))  # seconds
SHORT_WAIT = int(os.getenv("SHORT_WAIT", "5"))  # for "is it there?" probes
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "60"))
