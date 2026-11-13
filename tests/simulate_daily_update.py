"""Simulate one daily bill update against the sample database. CI runs this after load_sample_data.py.

LegiScan is faked: the master list says one bill changed, and getBill returns that bill with a
new change_hash and status. Everything else is real: the budget query, and the SQL that writes
raw.bills and raw.bill_versions.
"""
import copy
import json
from pathlib import Path

import psycopg

import update_bills

BILL_DIR = Path(__file__).parent / "fixtures" / "dataset_sample" / "OK" / "2026-2026_Regular_Session" / "bill"
bills = [json.loads(p.read_text())["bill"] for p in sorted(BILL_DIR.glob("*.json"))]
unchanged = bills[1]
changed = copy.deepcopy(bills[0])
changed["change_hash"] = "ci-new-hash"
changed["status"] = 4  # Passed

master = {
    "masterlist": {
        str(i): {"bill_id": b["bill_id"], "number": b["bill_number"], "change_hash": b["change_hash"]}
        for i, b in enumerate([changed, unchanged])
    }
}

fetched = []


def fake_call_api(op, **params):
    assert op == "getBill", op
    fetched.append(params["id"])
    return {"status": "OK", "bill": changed}


update_bills.call_api = fake_call_api

with psycopg.connect("") as conn:
    updated = update_bills.update_changed_bills(conn, master_data=master)
    with conn.cursor() as cur:
        stored_hash = cur.execute(
            "SELECT change_hash FROM raw.bills WHERE bill_id = %s", (changed["bill_id"],)
        ).fetchone()[0]
        versions = cur.execute(
            "SELECT COUNT(*) FROM raw.bill_versions WHERE bill_id = %s", (changed["bill_id"],)
        ).fetchone()[0]

assert fetched == [changed["bill_id"]], f"Only the changed bill should be fetched, got {fetched}"
assert updated == 1, updated
assert stored_hash == "ci-new-hash", stored_hash
assert versions == 2, f"Old version must be kept and new one added, got {versions}"
print("Daily update OK: fetched only the changed bill, stored its new hash, kept the old version.")
