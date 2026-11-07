"""Look at getMasterListRaw once, and compare its change_hash values to what's stored. Run: python src/probe_masterlist.py"""
import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from legiscan_client import call_api

load_dotenv()
SESSION_ID = 2219  # 2026 Regular Session

out = Path("data/probe/masterlist_raw.json")
if out.exists():
    data = json.loads(out.read_text())
else:
    data = call_api("getMasterListRaw", id=SESSION_ID)

out = Path("data/probe/masterlist_raw.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(data, indent=2))

bills = {k: v for k, v in data["masterlist"].items() if k != "session"}
print("Bills in master list:", len(bills))
print("Fields on one bill:", list(next(iter(bills.values())).keys()))
print("Sample:", next(iter(bills.values())))

with psycopg.connect(os.getenv("DATABASE_URL", "")) as conn, conn.cursor() as cur:
    cur.execute("SELECT bill_id, data->'bill'->>'change_hash' FROM raw.bills")
    stored = dict(cur.fetchall())

changed = [b for b in bills.values() if stored.get(b["bill_id"]) != b["change_hash"]]
missing = [b for b in bills.values() if b["bill_id"] not in stored]
print("Hash differs from stored:", len(changed))
print("Not in raw.bills at all:", len(missing))