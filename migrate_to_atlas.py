"""
migrate_to_atlas.py
Copies all collections from local MongoDB to Atlas.
Run once: python migrate_to_atlas.py
"""
import ssl
import certifi
from pymongo import MongoClient

# Local MongoDB
local = MongoClient("mongodb://localhost:27017/")
local_db = local["digital_Management"]

# Atlas MongoDB
ATLAS_URI = "mongodb+srv://nandanisonipraffulbhai8686_db_user:mShQgjGRaD9nfSr1@cluster0.tdlv6bx.mongodb.net/digital_Management?appName=Cluster0"
atlas = MongoClient(ATLAS_URI, tlsCAFile=certifi.where())
atlas_db = atlas["digital_Management"]

collections = ["patients", "doctors", "staff", "admin", "appointments", "hospitals", "prescriptions", "ratings", "bills"]

for col_name in collections:
    local_col = local_db[col_name]
    atlas_col = atlas_db[col_name]
    
    docs = list(local_col.find({}))
    if docs:
        # Remove _id to avoid duplicate key errors on re-run
        atlas_col.delete_many({})  # clear first
        atlas_col.insert_many(docs)
        print(f"✅ {col_name}: {len(docs)} documents migrated")
    else:
        print(f"⚠️  {col_name}: empty, skipped")

print("\n✅ Migration complete!")
