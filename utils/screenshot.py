"""Failure screenshot helper."""

import re
from datetime import datetime

from config import settings
from utils.logger import get_logger

log = get_logger(__name__)


def take_screenshot(driver, name: str) -> str | None:
    """Save a PNG for `name` and return its path (None if the capture failed)."""
    if driver is None:
        return None

    settings.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = settings.SCREENSHOT_DIR / f"{safe_name}_{timestamp}.png"

    try:
        driver.save_screenshot(str(path))
    except Exception as exc:  # a dead session must not mask the real failure
        log.warning("Screenshot could not be captured: %s", exc)
        return None

    log.info("Screenshot saved: %s", path)
    return str(path)
