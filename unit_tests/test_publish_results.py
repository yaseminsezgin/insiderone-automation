"""Unit tests for the run status derivation in scripts/publish_results.py."""

from collections import Counter

import pytest

from scripts.publish_results import run_status


@pytest.mark.parametrize(
    ("exit_status", "statuses", "expected"),
    [
        (0, ["passed", "passed"], "passed"),
        (1, ["passed", "failed", "skipped"], "failed"),
        (1, ["passed", "error"], "failed"),
        (4, [], "error"),
        (5, [], "error"),
        (2, ["passed"], "error"),
        (0, ["skipped", "skipped"], "error"),
        (None, ["passed"], "error"),
    ],
    ids=[
        "all-passed",
        "assertion-failure",
        "setup-error",
        "usage-error-no-tests",
        "no-tests-collected",
        "interrupted",
        "only-skipped",
        "missing-exit-status",
    ],
)
def test_run_status(exit_status, statuses, expected):
    assert run_status({"exit_status": exit_status}, Counter(statuses)) == expected
