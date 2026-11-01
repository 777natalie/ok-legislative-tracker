CREATE TABLE IF NOT EXISTS meta.datasets (
    session_id    INTEGER PRIMARY KEY,
    session_name  TEXT,
    dataset_hash  TEXT NOT NULL,
    loaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);