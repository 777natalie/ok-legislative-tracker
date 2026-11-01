import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
SESSION_ID = 2219
DATASET_DIR = Path(f"data/raw/dataset_{SESSION_ID}")


def read_all(folder):
    """Yield every JSON file in one folder of the dataset (bill, vote, people)."""
    for path in sorted(DATASET_DIR.rglob(f"{folder}/*.json")):
        yield json.loads(path.read_text())


bills = [
    (d["bill"]["bill_id"], d["bill"]["session_id"], d["bill"]["change_hash"], Jsonb(d))
    for d in read_all("bill")
]
roll_calls = [
    (d["roll_call"]["roll_call_id"], d["roll_call"]["bill_id"], Jsonb(d))
    for d in read_all("vote")
]
people = [
    (d["person"]["people_id"], d["person"]["person_hash"], Jsonb(d))
    for d in read_all("people")
]

with psycopg.connect(DATABASE_URL) as conn:
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

print(f"Loaded {len(bills)} bills, {len(roll_calls)} roll calls, {len(people)} people")