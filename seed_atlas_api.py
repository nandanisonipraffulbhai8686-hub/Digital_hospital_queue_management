"""
seed_atlas_api.py
Inserts data via Atlas Data API (HTTP) - works on any network.
Run: python seed_atlas_api.py
"""
import urllib.request
import json

# ── Atlas Data API config ──────────────────────────────────────
# You need to enable Data API in Atlas first:
# Atlas → App Services → Data API → Enable → Copy API Key
API_KEY    = "YOUR_API_KEY_HERE"
APP_ID     = "YOUR_APP_ID_HERE"  
BASE_URL   = f"https://data.mongodb-api.com/app/{APP_ID}/endpoint/data/v1"
DB         = "digital_Management"
DATA_SOURCE = "Cluster0"

def insert_many(collection, docs):
    url = f"{BASE_URL}/action/insertMany"
    payload = json.dumps({
        "dataSource": DATA_SOURCE,
        "database":   DB,
        "collection": collection,
        "documents":  docs
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type":  "application/json",
        "api-key":       API_KEY
    })
    with urllib.request.urlopen(req) as r:
        print(f"✅ {collection}: {r.read().decode()}")

insert_many("admin", [
    {"name": "Nandani", "username": "Nandani", "password": "nishi8686", "email": "nandani@hospital.com"}
])

insert_many("doctors", [
    {"name": "Dr. Priya Sharma",   "username": "dr_priya",   "password": "priya123",   "department": "Cardiology"},
    {"name": "Dr. Arjun Mehta",    "username": "dr_arjun",   "password": "arjun123",   "department": "Neurology"},
    {"name": "Dr. Neha Gupta",     "username": "dr_neha",    "password": "neha123",    "department": "Pediatrics"},
    {"name": "Dr. Ravi Patel",     "username": "dr_ravi",    "password": "ravi123",    "department": "Orthopedics"},
    {"name": "Dr. Sunita Rao",     "username": "dr_sunita",  "password": "sunita123",  "department": "Dermatology"},
    {"name": "Dr. Vikram Singh",   "username": "dr_vikram",  "password": "vikram123",  "department": "ENT"},
    {"name": "Dr. Kavita Desai",   "username": "dr_kavita",  "password": "kavita123",  "department": "Gynecology"},
    {"name": "Dr. Mahesh Trivedi", "username": "dr_mahesh",  "password": "mahesh123",  "department": "General Medicine"},
])

insert_many("staff", [
    {"name": "Ramesh Prajapati", "username": "staff_ramesh", "password": "ramesh123"},
    {"name": "Lata Mishra",      "username": "staff_lata",   "password": "lata123"},
    {"name": "Suresh Kapoor",    "username": "staff_suresh", "password": "suresh123"},
    {"name": "Geeta Pandey",     "username": "staff_geeta",  "password": "geeta123"},
    {"name": "Dinesh Solanki",   "username": "staff_dinesh", "password": "dinesh123"},
    {"name": "Anita Chauhan",    "username": "staff_anita",  "password": "anita123"},
])

print("\n✅ Done!")
