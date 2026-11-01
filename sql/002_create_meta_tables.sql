CREATE SCHEMA IF NOT EXISTS meta;

CREATE TABLE IF NOT EXISTS meta.api_calls (
    call_id      BIGSERIAL PRIMARY KEY,
    called_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    operation    TEXT NOT NULL,
    params       JSONB,
    status       TEXT,
    http_status  INTEGER
);