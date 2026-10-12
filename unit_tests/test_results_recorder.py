"""Unit tests for the pytest results recorder (no browser needed)."""

import json
from types import SimpleNamespace

import pytest

from utils.results_recorder import ResultsRecorder, _ci_metadata

NODEID = "tests/test_x.py::TestFlow::test_step"


def make_report(when, outcome, longrepr=None, start=100.0, duration=1.0, **extra):
    return SimpleNamespace(
        nodeid=NODEID,
        when=when,
        failed=outcome == "failed",
        skipped=outcome == "skipped",
        longrepr=longrepr,
        start=start,
        stop=start + duration,
        duration=duration,
        **extra,
    )


def make_session(collectonly=False):
    return SimpleNamespace(config=SimpleNamespace(option=SimpleNamespace(collectonly=collectonly)))


@pytest.fixture
def recorder(tmp_path):
    return ResultsRecorder(tmp_path / "results.json", "chrome", True, "https://example.com/")


def record(recorder, *reports):
    for report in reports:
        recorder.pytest_runtest_logreport(report)
    return recorder.tests[NODEID]


def test_passing_test_sums_phase_durations(recorder):
    entry = record(
        recorder,
        make_report("setup", "passed", duration=0.5),
        make_report("call", "passed", start=100.5, duration=2.0),
        make_report("teardown", "passed", start=102.5, duration=0.25),
    )
    assert entry["status"] == "passed"
    assert entry["duration_seconds"] == pytest.approx(2.75)
    assert entry["error_message"] is None
    assert entry["name"] == "test_step"


def test_call_failure_is_failed(recorder):
    entry = record(
        recorder,
        make_report("setup", "passed"),
        make_report("call", "failed", longrepr="AssertionError: boom"),
    )
    assert entry["status"] == "failed"
    assert entry["error_message"] == "AssertionError: boom"


def test_teardown_error_does_not_override_call_failure(recorder):
    entry = record(
        recorder,
        make_report("setup", "passed"),
        make_report("call", "failed", longrepr="AssertionError: boom"),
        make_report("teardown", "failed", longrepr="WebDriverException"),
    )
    assert entry["status"] == "failed"
    assert entry["error_message"] == "AssertionError: boom"


def test_setup_failure_is_error(recorder):
    entry = record(recorder, make_report("setup", "failed", longrepr="fixture broke"))
    assert entry["status"] == "error"


def test_teardown_failure_after_pass_is_error(recorder):
    entry = record(
        recorder,
        make_report("setup", "passed"),
        make_report("call", "passed"),
        make_report("teardown", "failed", longrepr="quit failed"),
    )
    assert entry["status"] == "error"


def test_setup_skip_is_skipped_with_reason(recorder):
    entry = record(
        recorder,
        make_report("setup", "skipped", longrepr=("conftest.py", 1, "Skipped: previous step failed")),
    )
    assert entry["status"] == "skipped"
    assert entry["error_message"] == "Skipped: previous step failed"


def test_skip_inside_test_body_is_skipped(recorder):
    entry = record(
        recorder,
        make_report("setup", "passed"),
        make_report("call", "skipped", longrepr=("test_x.py", 9, "Skipped: not today")),
    )
    assert entry["status"] == "skipped"


def test_xfail_is_skipped_with_reason(recorder):
    entry = record(
        recorder,
        make_report("setup", "passed"),
        make_report("call", "skipped", wasxfail="known bug"),
    )
    assert entry["status"] == "skipped"
    assert entry["error_message"] == "xfail: known bug"


def test_sessionfinish_writes_results_with_exit_status(recorder):
    recorder.pytest_sessionstart(make_session())
    record(recorder, make_report("setup", "passed"), make_report("call", "passed"))
    recorder.pytest_sessionfinish(make_session(), exitstatus=0)

    data = json.loads(recorder.output_path.read_text())
    assert data["run"]["browser"] == "chrome"
    assert data["run"]["exit_status"] == 0
    assert data["run"]["duration_seconds"] >= 0
    assert [t["status"] for t in data["tests"]] == ["passed"]
    assert "_finished" not in data["tests"][0]


def test_sessionfinish_with_no_tests_keeps_exit_status(recorder):
    recorder.pytest_sessionfinish(make_session(), exitstatus=4)
    data = json.loads(recorder.output_path.read_text())
    assert data["tests"] == []
    assert data["run"]["exit_status"] == 4


def test_collect_only_writes_nothing(recorder):
    recorder.pytest_sessionfinish(make_session(collectonly=True), exitstatus=0)
    assert not recorder.output_path.exists()


def test_ci_metadata_local(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert _ci_metadata() == {"source": "local", "branch": None, "commit_sha": None, "ci_run_url": None}


def test_ci_metadata_on_pull_request(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_HEAD_REF", "feature/x")
    monkeypatch.setenv("GITHUB_REF_NAME", "7/merge")
    monkeypatch.setenv("GITHUB_SHA", "mergesha")
    monkeypatch.setenv("COMMIT_SHA", "headsha")

    assert _ci_metadata() == {
        "source": "ci",
        "branch": "feature/x",
        "commit_sha": "headsha",
        "ci_run_url": "https://github.com/owner/repo/actions/runs/42",
    }


def test_ci_metadata_on_push_falls_back_to_ref_name_and_sha(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_HEAD_REF", "")
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    monkeypatch.delenv("COMMIT_SHA", raising=False)
    monkeypatch.setenv("GITHUB_SHA", "pushsha")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

    metadata = _ci_metadata()

    assert metadata["branch"] == "main"
    assert metadata["commit_sha"] == "pushsha"


def test_ci_metadata_without_run_id_has_no_run_url(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)

    metadata = _ci_metadata()

    assert metadata["source"] == "ci"
    assert metadata["ci_run_url"] is None


def test_long_error_message_keeps_last_2000_chars(recorder):
    longrepr = "head-" + "x" * 2500 + "-tail"
    entry = record(recorder, make_report("call", "failed", longrepr=longrepr))
    assert len(entry["error_message"]) == 2000
    assert entry["error_message"] == longrepr[-2000:]
    assert entry["error_message"].endswith("-tail")
