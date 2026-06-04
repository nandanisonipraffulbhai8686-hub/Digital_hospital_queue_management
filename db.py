import os
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["digital_Management"]

patients_col      = db["patients"]
doctors_col       = db["doctors"]
staff_col         = db["staff"]
admin_col         = db["admin"]
appointments_col  = db["appointments"]
hospitals_col     = db["hospitals"]
prescriptions_col = db["prescriptions"]

# ── NEW: ratings collection ────────────────────────────────────
# Stores one document per reviewed appointment.
# Schema:
#   appointment_id   : ObjectId  – reference to the appointment
#   patient_username : str       – who left the review
#   doctor           : str       – doctor name (for easy querying)
#   date             : str       – appointment date (YYYY-MM-DD)
#   rating           : int       – 1–5
#   review           : str       – free-text review
#   submitted_at     : datetime  – when review was saved
ratings_col = db["ratings"]

# Useful indexes (run once at startup or in a migration script)
ratings_col.create_index("doctor")
ratings_col.create_index("patient_username")
#ratings_col.create_index("appointment_id", unique=True)