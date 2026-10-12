"""Unit tests for scripts/publish_results.py."""

import json
import sys
from collections import Counter
from unittest.mock import MagicMock

import pytest

from scripts import publish_results
from scripts.publish_results import SCHEMA_FILE, publish, run_status


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


def make_results(run_uuid="uuid-1", statuses=("passed", "failed", "error", "skipped", "passed")):
    run = {
        "run_uuid": run_uuid,
        "source": "ci",
        "browser": "chrome",
        "headless": True,
        "base_url": "https://example.com/",
        "branch": "feature/x",
        "commit_sha": "abc",
        "ci_run_url": None,
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:01:00+00:00",
        "duration_seconds": 60.0,
        "exit_status": 1,
    }
    tests = [
        {
            "nodeid": f"tests/test_x.py::test_{i}",
            "name": f"test_{i}",
            "status": status,
            "duration_seconds": 1.0,
            "error_message": None,
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:01+00:00",
        }
        for i, status in enumerate(statuses)
    ]
    return {"run": run, "tests": tests}


def make_conn(fetched):
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = fetched
    return conn


def test_publish_returns_new_run_id_and_inserts_counts():
    conn = make_conn((7,))
    results = make_results()

    assert publish(conn, results) == 7

    params = conn.execute.call_args.args[1]
    assert params["run_uuid"] == "uuid-1"
    assert params["total"] == 5
    assert params["passed"] == 2
    assert params["failed"] == 1
    assert params["errors"] == 1
    assert params["skipped"] == 1
    assert params["status"] == "failed"
    assert params["exit_status"] == 1


def test_publish_inserts_every_test_with_run_id():
    conn = make_conn((7,))
    results = make_results()

    publish(conn, results)

    cur = conn.cursor.return_value.__enter__.return_value
    cur.executemany.assert_called_once()
    rows = cur.executemany.call_args.args[1]
    assert [row["nodeid"] for row in rows] == [t["nodeid"] for t in results["tests"]]
    assert {row["run_id"] for row in rows} == {7}


def test_publish_already_stored_run_is_skipped():
    conn = make_conn(None)

    assert publish(conn, make_results()) is None

    conn.cursor.assert_not_called()
    conn.cursor.return_value.__enter__.return_value.executemany.assert_not_called()


def test_main_applies_schema_and_publishes_each_file(tmp_path, monkeypatch, capsys):
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    first.write_text(json.dumps(make_results("uuid-1")))
    second.write_text(json.dumps(make_results("uuid-2")))

    conn = MagicMock()
    connect = MagicMock()
    connect.return_value.__enter__.return_value = conn
    monkeypatch.setattr(publish_results.psycopg, "connect", connect)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/metrics")
    published = []
    run_ids = iter([7, None])

    def fake_publish(c, results):
        published.append((c, results["run"]["run_uuid"]))
        return next(run_ids)

    monkeypatch.setattr(publish_results, "publish", fake_publish)
    monkeypatch.setattr(sys, "argv", ["publish_results.py", str(first), str(second)])

    assert publish_results.main() == 0

    connect.assert_called_once_with("postgresql://u:p@db:5432/metrics")
    conn.execute.assert_called_once_with(SCHEMA_FILE.read_text())
    conn.commit.assert_called_once()
    assert published == [(conn, "uuid-1"), (conn, "uuid-2")]
    out = capsys.readouterr().out
    assert f"{first}: stored run #7 (chrome, 5 tests, 60.0s)" in out
    assert f"{second}: run uuid-2 already stored, skipped" in out


def test_main_falls_back_to_default_database_url(tmp_path, monkeypatch):
    results_file = tmp_path / "results.json"
    results_file.write_text(json.dumps(make_results()))

    connect = MagicMock()
    monkeypatch.setattr(publish_results.psycopg, "connect", connect)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(publish_results, "publish", lambda conn, results: 7)
    monkeypatch.setattr(sys, "argv", ["publish_results.py", str(results_file)])

    assert publish_results.main() == 0

    connect.assert_called_once_with("postgresql://qa:qa@localhost:5432/test_metrics")
