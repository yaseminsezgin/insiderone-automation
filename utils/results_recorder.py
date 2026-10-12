"""Collects per-test outcomes and durations into a JSON file for the metrics pipeline."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

_PHASES = ("setup", "call", "teardown")


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _ci_metadata() -> dict:
    if os.getenv("GITHUB_ACTIONS") != "true":
        return {"source": "local", "branch": None, "commit_sha": None, "ci_run_url": None}

    run_url = None
    if os.getenv("GITHUB_RUN_ID"):
        run_url = (
            f"{os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{os.getenv('GITHUB_REPOSITORY')}/actions/runs/{os.getenv('GITHUB_RUN_ID')}"
        )
    return {
        "source": "ci",
        "branch": os.getenv("GITHUB_HEAD_REF") or os.getenv("GITHUB_REF_NAME"),
        "commit_sha": os.getenv("GITHUB_SHA"),
        "ci_run_url": run_url,
    }


class ResultsRecorder:
    """Pytest plugin: one entry per test, merged from its setup/call/teardown reports."""

    def __init__(self, output_path: Path, browser: str, headless: bool, base_url: str):
        self.output_path = output_path
        self.run = {
            "run_uuid": str(uuid.uuid4()),
            "browser": browser,
            "headless": headless,
            "base_url": base_url,
            **_ci_metadata(),
        }
        self.tests: dict[str, dict] = {}
        self.session_start: float | None = None

    def pytest_sessionstart(self, session):
        self.session_start = datetime.now(timezone.utc).timestamp()

    def pytest_runtest_logreport(self, report):
        if report.when not in _PHASES:
            return

        entry = self.tests.setdefault(
            report.nodeid,
            {
                "nodeid": report.nodeid,
                "name": report.nodeid.split("::")[-1],
                "status": "passed",
                "duration_seconds": 0.0,
                "error_message": None,
                "started_at": _iso(report.start),
                "_finished": report.stop,
            },
        )
        entry["duration_seconds"] += report.duration
        entry["_finished"] = max(entry["_finished"], report.stop)

        if report.failed:
            entry["status"] = "failed" if report.when == "call" else "error"
            if entry["error_message"] is None:
                entry["error_message"] = str(report.longrepr)[-2000:]
        elif report.skipped and report.when == "setup":
            entry["status"] = "skipped"
            if isinstance(report.longrepr, tuple):
                entry["error_message"] = report.longrepr[2]

    def pytest_sessionfinish(self, session):
        finished = datetime.now(timezone.utc).timestamp()
        tests = []
        for entry in self.tests.values():
            entry["finished_at"] = _iso(entry.pop("_finished"))
            entry["duration_seconds"] = round(entry["duration_seconds"], 3)
            tests.append(entry)

        started = self.session_start or finished
        self.run.update(
            started_at=_iso(started),
            finished_at=_iso(finished),
            duration_seconds=round(finished - started, 3),
        )

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps({"run": self.run, "tests": tests}, indent=2))
