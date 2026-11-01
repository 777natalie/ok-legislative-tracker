import csv
import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("LEGISCAN_API_KEY")
SESSION_ID = 2219  # 2026 Regular Session

# 1. Extract: ask LegiScan for everyone in this session
params = {"key": API_KEY, "op": "getSessionPeople", "id": SESSION_ID}
response = requests.get("https://api.legiscan.com/", params=params, timeout=30)
response.raise_for_status()
data = response.json()

if data["status"] != "OK":
    raise SystemExit(f"LegiScan returned an error: {data}")

# 2. Save the raw response exactly as it came back
os.makedirs("data/raw", exist_ok=True)
with open(f"data/raw/session_people_{SESSION_ID}.json", "w") as f:
    json.dump(data, f, indent=2)

# 3. Keep just the columns needed and write a CSV
people = data["sessionpeople"]["people"]
fields = ["people_id", "name", "party", "role", "district"]

with open("data/legislators.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for person in people:
        writer.writerow({field: person.get(field) for field in fields})

print(f"Saved {len(people)} legislators to data/legislators.csv")