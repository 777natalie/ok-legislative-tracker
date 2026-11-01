"""Run the whole pipeline: check LegiScan for new datasets, load them, run dbt.

Usage:
    python src/run_pipeline.py           # normal run
    python src/run_pipeline.py --force   # check the dataset list even if already checked this week
"""
import argparse
import base64
import io
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

from legiscan_client import call_api

load_dotenv()
# Empty means "use the standard PGHOST / PGUSER / PGPASSWORD / PGDATABASE variables"
DATABASE_URL = os.getenv("DATABASE_URL", "")
STATE = os.getenv("LEGISCAN_STATE", "OK")
TRACK_FROM_YEAR = int(os.getenv("TRACK_FROM_YEAR", "2026"))
RAW_DIR = Path(os.getenv("RAW_DIR", "data/raw"))
DBT_DIR = Path(__file__).resolve().parent.parent / "dbt"


# ---------- When to ask LegiScan for the dataset list ----------

def last_dataset_publication(now):
    """LegiScan publishes datasets on Sundays at 5am Eastern.
    Return the most recent publication time in UTC. 10:00 UTC is always
    after 5am Eastern, in both standard and daylight time."""
    days_since_sunday = (now.weekday() + 1) % 7  # Monday=0 ... Sunday=6
    sunday = (now - timedelta(days=days_since_sunday)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    if sunday > now:
        sunday -= timedelta(days=7)
    return sunday


def dataset_list_checked_since(conn, since):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM meta.api_calls "
            "WHERE operation = 'getDatasetList' AND status = 'OK' AND called_at >= %s)",
            (since,),
        )
        return cur.fetchone()[0]


# ---------- Which sessions, and which ones changed ----------

def sessions_to_track(dataset_list):
    """Every session that ends in TRACK_FROM_YEAR or later, including special sessions."""
    return [d for d in dataset_list if int(d["year_end"]) >= TRACK_FROM_YEAR]


def stored_hash(conn, session_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT dataset_hash FROM meta.datasets WHERE session_id = %s", (session_id,)
        )
        row = cur.fetchone()
        return row[0] if row else None


# ---------- Extract ----------

def download_dataset(ds):
    data = call_api("getDataset", id=ds["session_id"], access_key=ds["access_key"])["dataset"]
    out_dir = RAW_DIR / f"dataset_{ds['session_id']}"
    zip_bytes = base64.b64decode(data["zip"])
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        z.extractall(out_dir)
    return out_dir


# ---------- Load ----------

def read_all(dataset_dir, folder):
    for path in sorted(dataset_dir.rglob(f"{folder}/*.json")):
        yield json.loads(path.read_text())


def load_dataset(conn, dataset_dir):
    bills = [
        (d["bill"]["bill_id"], d["bill"]["session_id"], d["bill"]["change_hash"], Jsonb(d))
        for d in read_all(dataset_dir, "bill")
    ]
    roll_calls = [
        (d["roll_call"]["roll_call_id"], d["roll_call"]["bill_id"], Jsonb(d))
        for d in read_all(dataset_dir, "vote")
    ]
    people = [
        (d["person"]["people_id"], d["person"]["person_hash"], Jsonb(d))
        for d in read_all(dataset_dir, "people")
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO raw.bills (bill_id, session_id, change_hash, data)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (bill_id) DO UPDATE
            SET session_id = EXCLUDED.session_id,
                change_hash = EXCLUDED.change_hash,
                data = EXCLUDED.data,
                loaded_at = now()
            """,
            bills,
        )
        cur.executemany(
            """
            INSERT INTO raw.roll_calls (roll_call_id, bill_id, data)
            VALUES (%s, %s, %s)
            ON CONFLICT (roll_call_id) DO UPDATE
            SET bill_id = EXCLUDED.bill_id,
                data = EXCLUDED.data,
                loaded_at = now()
            """,
            roll_calls,
        )
        cur.executemany(
            """
            INSERT INTO raw.people (people_id, person_hash, data)
            VALUES (%s, %s, %s)
            ON CONFLICT (people_id) DO UPDATE
            SET person_hash = EXCLUDED.person_hash,
                data = EXCLUDED.data,
                loaded_at = now()
            """,
            people,
        )
    return len(bills), len(roll_calls), len(people)


def record_dataset(conn, ds):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO meta.datasets (session_id, session_name, dataset_hash)
            VALUES (%s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE
            SET session_name = EXCLUDED.session_name,
                dataset_hash = EXCLUDED.dataset_hash,
                loaded_at = now()
            """,
            (ds["session_id"], ds["session_name"], ds["dataset_hash"]),
        )


# ---------- Transform ----------

def run_dbt():
    # --profiles-dir . uses dbt/profiles.yml from the repo, which reads the same PG* variables
    result = subprocess.run(["dbt", "build", "--profiles-dir", "."], cwd=DBT_DIR)
    if result.returncode != 0:
        sys.exit("dbt build failed. Marts were not updated.")


# ---------- Main ----------

def main(force=False):
    print(f"Target database: {os.getenv('PGHOST', 'localhost')} / {os.getenv('PGDATABASE', '?')}")
    now = datetime.now(timezone.utc)
    published = last_dataset_publication(now)

    with psycopg.connect(DATABASE_URL) as conn:
        if not force and dataset_list_checked_since(conn, published):
            print(
                f"Dataset list already checked since LegiScan's last publication "
                f"({published:%Y-%m-%d %H:%M} UTC). No API calls needed."
            )
        else:
            dataset_list = call_api("getDatasetList", state=STATE)["datasetlist"]
            tracked = sessions_to_track(dataset_list)
            print(f"Tracking {len(tracked)} session(s) ending in {TRACK_FROM_YEAR} or later:")

            for ds in tracked:
                name = ds["session_name"]
                if stored_hash(conn, ds["session_id"]) == ds["dataset_hash"]:
                    print(f"  {name}: unchanged, skipping")
                    continue

                print(f"  {name}: new or changed, downloading")
                dataset_dir = download_dataset(ds)
                bills, roll_calls, people = load_dataset(conn, dataset_dir)
                # The hash is saved in the same transaction as the load,
                # so a failed load is retried next run instead of being skipped.
                record_dataset(conn, ds)
                conn.commit()
                print(f"    loaded {bills} bills, {roll_calls} roll calls, {people} people")

    run_dbt()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Check the dataset list even if it was already checked this week",
    )
    main(force=parser.parse_args().force)