import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("LEGISCAN_API_KEY")

url = "https://api.legiscan.com/"
params = {"key": API_KEY, "op": "getSessionList", "state": "OK"}

response = requests.get(url, params=params)
data = response.json()

print("Status:", data["status"])
for session in data["sessions"][:5]:
    print(session["session_id"], session["session_name"])