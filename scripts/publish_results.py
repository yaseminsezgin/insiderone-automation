"""Write one or more pytest results.json files into the test-metrics PostgreSQL database.

Usage:
    python scripts/publish_results.py [reports/results.json ...]

The connection string comes from DATABASE_URL. Publishing is idempotent: a run whose
run_uuid is already stored is skipped, so CI artifacts can be re-imported safely.
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import psycopg

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = PROJECT_ROOT / "db" / "schema.sql"
DEFAULT_RESULTS = PROJECT_ROOT / "reports" / "results.json"
DEFAULT_DATABASE_URL = "postgresql://qa:qa@localhost:5432/test_metrics"


def publish(conn: psycopg.Connection, results: dict) -> int | None:
    run, tests = results["run"], results["tests"]
    counts = Counter(test["status"] for test in tests)
    status = "failed" if counts["failed"] or counts["error"] else "passed"

    with conn.transaction():
        run_id = conn.execute(
            """
            INSERT INTO test_runs (
                run_uuid, source, browser, headless, base_url, branch, commit_sha,
                ci_run_url, started_at, finished_at, duration_seconds,
                total, passed, failed, errors, skipped, status
            ) VALUES (
                %(run_uuid)s, %(source)s, %(browser)s, %(headless)s, %(base_url)s,
                %(branch)s, %(commit_sha)s, %(ci_run_url)s, %(started_at)s,
                %(finished_at)s, %(duration_seconds)s, %(total)s, %(passed)s,
                %(failed)s, %(errors)s, %(skipped)s, %(status)s
            )
            ON CONFLICT (run_uuid) DO NOTHING
            RETURNING id
            """,
            {
                **run,
                "total": len(tests),
                "passed": counts["passed"],
                "failed": counts["failed"],
                "errors": counts["error"],
                "skipped": counts["skipped"],
                "status": status,
            },
        ).fetchone()
        if run_id is None:
            return None

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO test_results (
                    run_id, nodeid, name, status, duration_seconds,
                    error_message, started_at, finished_at
                ) VALUES (
                    %(run_id)s, %(nodeid)s, %(name)s, %(status)s, %(duration_seconds)s,
                    %(error_message)s, %(started_at)s, %(finished_at)s
                )
                """,
                [{**test, "run_id": run_id[0]} for test in tests],
            )
    return run_id[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", type=Path, default=[DEFAULT_RESULTS])
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    with psycopg.connect(database_url) as conn:
        conn.execute(SCHEMA_FILE.read_text())
        conn.commit()

        for path in args.files:
            results = json.loads(path.read_text())
            run_id = publish(conn, results)
            run = results["run"]
            if run_id is None:
                print(f"{path}: run {run['run_uuid']} already stored, skipped")
            else:
                print(
                    f"{path}: stored run #{run_id} ({run['browser']}, "
                    f"{len(results['tests'])} tests, {run['duration_seconds']}s)"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
