"""Load the sample dataset into an empty database, twice. CI runs this before dbt build.

The second load checks that the upserts are idempotent: row counts must not change,
and bill_versions must not get duplicate versions.

Usage (PG* variables point at a throwaway database):
    PYTHONPATH=src python tests/load_sample_data.py
"""
from pathlib import Path

import psycopg

from run_pipeline import load_dataset

SAMPLE = Path(__file__).parent / "fixtures" / "dataset_sample"
TABLES = ("bills", "roll_calls", "people", "bill_versions")


def counts(conn):
    with conn.cursor() as cur:
        return {t: cur.execute(f"SELECT COUNT(*) FROM raw.{t}").fetchone()[0] for t in TABLES}


with psycopg.connect("") as conn:
    load_dataset(conn, SAMPLE)
    conn.commit()
    first = counts(conn)
    load_dataset(conn, SAMPLE)
    conn.commit()
    second = counts(conn)

print("Loaded:", first)
assert first == second, f"Reloading changed row counts: {first} -> {second}"
assert first == {"bills": 2, "roll_calls": 7, "people": 154, "bill_versions": 2}, first
