CREATE TABLE IF NOT EXISTS test_runs (
    id               BIGSERIAL PRIMARY KEY,
    run_uuid         UUID        NOT NULL UNIQUE,
    source           TEXT        NOT NULL,
    browser          TEXT        NOT NULL,
    headless         BOOLEAN     NOT NULL,
    base_url         TEXT,
    branch           TEXT,
    commit_sha       TEXT,
    ci_run_url       TEXT,
    started_at       TIMESTAMPTZ NOT NULL,
    finished_at      TIMESTAMPTZ NOT NULL,
    duration_seconds NUMERIC(10, 3) NOT NULL,
    total            INTEGER     NOT NULL,
    passed           INTEGER     NOT NULL,
    failed           INTEGER     NOT NULL,
    errors           INTEGER     NOT NULL,
    skipped          INTEGER     NOT NULL,
    status           TEXT        NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS test_results (
    id               BIGSERIAL PRIMARY KEY,
    run_id           BIGINT      NOT NULL REFERENCES test_runs (id) ON DELETE CASCADE,
    nodeid           TEXT        NOT NULL,
    name             TEXT        NOT NULL,
    status           TEXT        NOT NULL CHECK (status IN ('passed', 'failed', 'error', 'skipped')),
    duration_seconds NUMERIC(10, 3) NOT NULL,
    error_message    TEXT,
    started_at       TIMESTAMPTZ NOT NULL,
    finished_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_test_runs_started_at ON test_runs (started_at);
CREATE INDEX IF NOT EXISTS idx_test_results_run_id ON test_results (run_id);
CREATE INDEX IF NOT EXISTS idx_test_results_started_at ON test_results (started_at);
