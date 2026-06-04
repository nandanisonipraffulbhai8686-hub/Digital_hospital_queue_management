"""
seed_atlas.py
Inserts essential admin, doctor, and staff data into Atlas.
Run: python seed_atlas.py
"""
import certifi
from pymongo import MongoClient

ATLAS_URI = "mongodb+srv://nandanisonipraffulbhai8686_db_user:mShQgjGRaD9nfSr1@cluster0.tdlv6bx.mongodb.net/digital_Management?appName=Cluster0"
client = MongoClient(ATLAS_URI, tlsCAFile=certifi.where())
db = client["digital_Management"]

# ── Admin ──────────────────────────────────────────────────────
db["admin"].delete_many({})
db["admin"].insert_many([
    {"name": "Nandani", "username": "Nandani", "password": "nishi8686", "email": "nandani@hospital.com"}
])
print("✅ Admin inserted")

# ── Doctors ────────────────────────────────────────────────────
db["doctors"].delete_many({})
db["doctors"].insert_many([
    {"name": "Dr. Priya Sharma",   "username": "dr_priya",   "password": "priya123",   "department": "Cardiology"},
    {"name": "Dr. Arjun Mehta",    "username": "dr_arjun",   "password": "arjun123",   "department": "Neurology"},
    {"name": "Dr. Neha Gupta",     "username": "dr_neha",    "password": "neha123",    "department": "Pediatrics"},
    {"name": "Dr. Ravi Patel",     "username": "dr_ravi",    "password": "ravi123",    "department": "Orthopedics"},
    {"name": "Dr. Sunita Rao",     "username": "dr_sunita",  "password": "sunita123",  "department": "Dermatology"},
    {"name": "Dr. Vikram Singh",   "username": "dr_vikram",  "password": "vikram123",  "department": "ENT"},
    {"name": "Dr. Kavita Desai",   "username": "dr_kavita",  "password": "kavita123",  "department": "Gynecology"},
    {"name": "Dr. Mahesh Trivedi", "username": "dr_mahesh",  "password": "mahesh123",  "department": "General Medicine"},
])
print("✅ Doctors inserted")

# ── Staff ──────────────────────────────────────────────────────
db["staff"].delete_many({})
db["staff"].insert_many([
    {"name": "Ramesh Prajapati", "username": "staff_ramesh", "password": "ramesh123"},
    {"name": "Lata Mishra",      "username": "staff_lata",   "password": "lata123"},
    {"name": "Suresh Kapoor",    "username": "staff_suresh", "password": "suresh123"},
    {"name": "Geeta Pandey",     "username": "staff_geeta",  "password": "geeta123"},
    {"name": "Dinesh Solanki",   "username": "staff_dinesh", "password": "dinesh123"},
    {"name": "Anita Chauhan",    "username": "staff_anita",  "password": "anita123"},
])
print("✅ Staff inserted")

print("\n✅ Atlas seeding complete! Your app is ready to use.")
client.close()
