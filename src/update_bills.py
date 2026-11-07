"""Daily bill updates: 1 master list call, then getBill only for changed bills, within budget.

Run:          python src/update_bills.py
Test, free:   python src/update_bills.py --from-file data/probe/masterlist_raw.json --dry-run
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

from legiscan_client import MONTHLY_LIMIT, call_api, calls_this_month

load_dotenv()
MAX_BILLS_PER_RUN = int(os.getenv("MAX_BILLS_PER_RUN", "200"))
RESERVED_CALLS = 50  # kept free for the weekly dataset job


def todays_budget(conn):
    """Remaining monthly calls, spread evenly over the days left (today included)."""
    today = date.today()
    days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    remaining = MONTHLY_LIMIT - RESERVED_CALLS - calls_this_month(conn)
    return max(0, min(MAX_BILLS_PER_RUN, remaining // days_left))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-file", help="Use a saved master list instead of calling the API")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fetched, fetch nothing")
    args = parser.parse_args()

    with psycopg.connect(os.getenv("DATABASE_URL", "")) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(session_id) FROM raw.bills")
            session_id = cur.fetchone()[0]
            cur.execute("SELECT bill_id, change_hash FROM raw.bills WHERE session_id = %s", (session_id,))
            stored = dict(cur.fetchall())

        if args.from_file:
            data = json.loads(Path(args.from_file).read_text())
        else:
            data = call_api("getMasterListRaw", id=session_id)

        master = [b for k, b in data["masterlist"].items() if k != "session"]
        changed = sorted(
            (b for b in master if stored.get(b["bill_id"]) != b["change_hash"]),
            key=lambda b: b["bill_id"],
        )
        budget = todays_budget(conn)
        to_fetch = changed[:budget]

        print(f"Session {session_id}: {len(master)} bills, {len(changed)} changed or new.")
        print(f"Budget today: {budget}. Fetching {len(to_fetch)}, leaving {len(changed) - len(to_fetch)} for later runs.")
        if args.dry_run:
            for b in to_fetch[:20]:
                print("  would fetch", b["bill_id"], b["number"])
            return

        for b in to_fetch:
            bill = call_api("getBill", id=b["bill_id"])["bill"]
            payload = Jsonb({"bill": bill})  # same shape as the dataset files
            with conn.transaction(), conn.cursor() as cur:
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
            print("  updated", bill["bill_id"], b["number"])


if __name__ == "__main__":
    main()