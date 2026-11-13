"""Quick check that the LegiScan API key works: prints a few Oklahoma sessions.

Uses one API call, made through call_api, so it is budget-checked and logged like every other call.

Usage: python src/check_api_key.py
"""
from legiscan_client import call_api

data = call_api("getSessionList", state="OK")
for session in data["sessions"][:5]:
    print(session["session_id"], session["session_name"])
