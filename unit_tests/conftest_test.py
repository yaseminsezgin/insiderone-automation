"""Unit tests for the pytest hook wiring in the root conftest.py."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import conftest
from config import settings
from utils.results_recorder import ResultsRecorder


def make_config(options):
    return SimpleNamespace(
        addinivalue_line=MagicMock(),
        getoption=options.__getitem__,
        pluginmanager=MagicMock(),
    )


def test_pytest_configure_registers_results_recorder_with_cli_options():
    config = make_config({"--browser": "firefox", "--headless": True})

    conftest.pytest_configure(config)

    config.pluginmanager.register.assert_called_once()
    plugin, name = config.pluginmanager.register.call_args.args
    assert name == "results_recorder"
    assert isinstance(plugin, ResultsRecorder)
    assert plugin.run["browser"] == "firefox"
    assert plugin.run["headless"] is True
    assert plugin.run["base_url"] == settings.BASE_URL
    assert plugin.output_path == settings.RESULTS_FILE
