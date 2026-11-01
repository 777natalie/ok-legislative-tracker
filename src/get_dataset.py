import base64
import io
import json
import zipfile
from pathlib import Path

from legiscan_client import call_api

SESSION_ID = 2219  # 2026 Regular Session
STATE_FILE = Path("data/state.json")
OUT_DIR = Path(f"data/raw/dataset_{SESSION_ID}")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# 1. Find this session's dataset and its current hash
datasets = call_api("getDatasetList", state="OK")["datasetlist"]
match = next((d for d in datasets if d["session_id"] == SESSION_ID), None)
if match is None:
    raise SystemExit(f"No dataset found for session {SESSION_ID}")

# 2. Skip the download if the hash hasn't changed since last time
state = load_state()
hash_key = f"dataset_hash_{SESSION_ID}"
if state.get(hash_key) == match["dataset_hash"] and OUT_DIR.exists():
    print("Dataset unchanged since last download. Skipping.")
    raise SystemExit(0)

# 3. Download, decode the Base64, and unzip
dataset = call_api("getDataset", id=SESSION_ID, access_key=match["access_key"])["dataset"]
zip_bytes = base64.b64decode(dataset["zip"])
with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
    z.extractall(OUT_DIR)

# 4. Remember the hash for next time
state[hash_key] = match["dataset_hash"]
save_state(state)

# 5. Summary
bills = list(OUT_DIR.rglob("bill/*.json"))
votes = list(OUT_DIR.rglob("vote/*.json"))
people = list(OUT_DIR.rglob("people/*.json"))
print(f"Downloaded {match['session_name']}")
print(f"  Bills:      {len(bills)}")
print(f"  Roll calls: {len(votes)}")
print(f"  People:     {len(people)}")