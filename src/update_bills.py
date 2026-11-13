"""Daily bill updates: 1 master list call, then getBill only for changed bills, within budget.

Run alone:    python src/update_bills.py
Test, free:   python src/update_bills.py --from-file data/probe/masterlist_raw.json --dry-run
Also called by run_pipeline.py.
"""
import argparse
import calendar
import json
import os
from datetime import date
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

from legiscan_client import MONTHLY_LIMIT, BudgetExceeded, call_api, calls_this_month

load_dotenv()
MAX_BILLS_PER_RUN = int(os.getenv("MAX_BILLS_PER_RUN", "200"))
RESERVED_CALLS = 50  # kept free for the weekly dataset job


def todays_budget(conn):
    """Remaining monthly calls, spread evenly over the days left (today included)."""
    today = date.today()
    days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    remaining = MONTHLY_LIMIT - RESERVED_CALLS - calls_this_month(conn)
    return max(0, min(MAX_BILLS_PER_RUN, remaining // days_left))


def find_changed_bills(master, stored):
    """Bills that are new or whose change_hash differs from the stored one, by bill_id."""
    return sorted(
        (b for b in master if stored.get(b["bill_id"]) != b["change_hash"]),
        key=lambda b: b["bill_id"],
    )


def update_changed_bills(conn, master_data=None, dry_run=False):
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(session_id) FROM raw.bills")
        session_id = cur.fetchone()[0]
        cur.execute("SELECT bill_id, change_hash FROM raw.bills WHERE session_id = %s", (session_id,))
        stored = dict(cur.fetchall())
    budget = todays_budget(conn)
    conn.commit()  # close the read transaction so each bill below commits on its own

    data = master_data or call_api("getMasterListRaw", id=session_id)
    master = [b for k, b in data["masterlist"].items() if k != "session"]
    changed = find_changed_bills(master, stored)
    to_fetch = changed[:budget]

    print(f"Session {session_id}: {len(master)} bills, {len(changed)} changed or new.")
    print(f"Budget today: {budget}. Fetching {len(to_fetch)}, leaving {len(changed) - len(to_fetch)} for later runs.")
    if dry_run:
        for b in to_fetch[:20]:
            print("  would fetch", b["bill_id"], b["number"])
        return 0

    updated = 0
    for b in to_fetch:
        try:
            bill = call_api("getBill", id=b["bill_id"])["bill"]
        except BudgetExceeded as e:
            print(f"  stopping early: {e}")
            break
        payload = Jsonb({"bill": bill})  # same shape as the dataset files
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO raw.bill_versions (bill_id, change_hash, source, data)
                   VALUES (%s, %s, 'getBill', %s)
                   ON CONFLICT (bill_id, change_hash) DO NOTHING""",
                (bill["bill_id"], bill["change_hash"], payload),
            )
            cur.execute(
                """INSERT INTO raw.bills (bill_id, session_id, change_hash, data)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (bill_id) DO UPDATE
                   SET change_hash = EXCLUDED.change_hash,
                       data        = EXCLUDED.data,
                       loaded_at   = now()""",
                (bill["bill_id"], session_id, bill["change_hash"], payload),
            )
        conn.commit()  # this bill is saved in both tables, even if a later one fails
        updated += 1
        print("  updated", bill["bill_id"], b["number"])
    return updated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-file", help="Use a saved master list instead of calling the API")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fetched, fetch nothing")
    args = parser.parse_args()
    data = json.loads(Path(args.from_file).read_text()) if args.from_file else None
    with psycopg.connect(os.getenv("DATABASE_URL", "")) as conn:
        update_changed_bills(conn, data, args.dry_run)


if __name__ == "__main__":
    main()