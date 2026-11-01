import os
import time

import psycopg
import requests
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

load_dotenv()
API_URL = "https://api.legiscan.com/"
API_KEY = os.getenv("LEGISCAN_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "")
MONTHLY_LIMIT = int(os.getenv("LEGISCAN_MONTHLY_LIMIT", "8000"))
MIN_SECONDS_BETWEEN_CALLS = 0.5

_last_call_time = 0.0


class BudgetExceeded(Exception):
    """Raised when this month's LegiScan calls reach the safety limit."""


class LegiScanError(Exception):
    """Raised when LegiScan returns anything other than status OK."""


def calls_this_month(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM meta.api_calls "
            "WHERE called_at >= date_trunc('month', now())"
        )
        return cur.fetchone()[0]


def call_api(op, **params):
    """Make one LegiScan call: check the budget, rate-limit, log it, check status."""
    global _last_call_time

    with psycopg.connect(DATABASE_URL) as conn:
        used = calls_this_month(conn)
        if used >= MONTHLY_LIMIT:
            raise BudgetExceeded(
                f"{used} LegiScan calls this month (limit {MONTHLY_LIMIT}). Not calling {op}."
            )

        wait = MIN_SECONDS_BETWEEN_CALLS - (time.monotonic() - _last_call_time)
        if wait > 0:
            time.sleep(wait)

        response = requests.get(
            API_URL, params={"key": API_KEY, "op": op, **params}, timeout=60
        )
        _last_call_time = time.monotonic()

        try:
            data = response.json()
        except ValueError:
            data = {}
        status = data.get("status")

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO meta.api_calls (operation, params, status, http_status) "
                "VALUES (%s, %s, %s, %s)",
                (op, Jsonb(params), status, response.status_code),
            )

    response.raise_for_status()
    if status != "OK":
        raise LegiScanError(f"{op} failed: {data.get('alert', data)}")
    return data