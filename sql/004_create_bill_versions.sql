CREATE TABLE IF NOT EXISTS raw.bill_versions (
    bill_id      INTEGER     NOT NULL,
    change_hash  TEXT        NOT NULL,
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    source       TEXT        NOT NULL,          -- 'dataset' or 'getBill'
    data         JSONB       NOT NULL,
    PRIMARY KEY (bill_id, change_hash)
);

-- Backfill: every bill you already have becomes its first version.
INSERT INTO raw.bill_versions (bill_id, change_hash, source, data)
SELECT bill_id, data->'bill'->>'change_hash', 'dataset', data
FROM raw.bills
ON CONFLICT (bill_id, change_hash) DO NOTHING;