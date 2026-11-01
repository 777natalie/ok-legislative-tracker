CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.bills (
    bill_id      INTEGER PRIMARY KEY,
    session_id   INTEGER NOT NULL,
    change_hash  TEXT NOT NULL,
    data         JSONB NOT NULL,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.roll_calls (
    roll_call_id INTEGER PRIMARY KEY,
    bill_id      INTEGER NOT NULL,
    data         JSONB NOT NULL,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.people (
    people_id    INTEGER PRIMARY KEY,
    person_hash  TEXT NOT NULL,
    data         JSONB NOT NULL,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);