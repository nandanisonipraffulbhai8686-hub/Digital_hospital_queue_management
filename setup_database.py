# -*- coding: utf-8 -*-
"""
Database Setup Script for Digital Hospital Queue System
This script populates MongoDB with sample Indian data
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
import random

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["digital_hospital_queue"]

# Get collections
patients_col = db["patients"]
doctors_col = db["doctors"]
staff_col = db["staff"]
admin_col = db["admin"]
appointments_col = db["appointments"]
hospitals_col = db["hospitals"]
prescriptions_col = db["prescriptions"]
ratings_col = db["ratings"]

# Clear existing data
print("Clearing existing collections...")
patients_col.delete_many({})
doctors_col.delete_many({})
staff_col.delete_many({})
admin_col.delete_many({})
appointments_col.delete_many({})
hospitals_col.delete_many({})
prescriptions_col.delete_many({})
ratings_col.delete_many({})

# ==================== ADMIN DATA ====================
print("Adding Admin users...")
admin_users = [
    {
        "name": "Raj Kumar",
        "username": "admin",
        "password": "admin123",
        "email": "admin@hospital.com",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Priya Sharma",
        "username": "admin2",
        "password": "admin123",
        "email": "admin2@hospital.com",
        "created_at": datetime.utcnow()
    }
]
admin_col.insert_many(admin_users)
print(f"✓ Added {len(admin_users)} admin users")

# ==================== PATIENT DATA ====================
print("Adding Patient data...")
patients = [
    {
        "name": "Hitu Patel",
        "username": "hitu",
        "password": "hitu@123",
        "email": "hitu.patel@email.com",
        "age": 28,
        "gender": "Female",
        "phone": "9876543210",
        "address": "Mumbai, Maharashtra",
        "medical_history": "None",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Nishi Sharma",
        "username": "nishi",
        "password": "nishi@123",
        "email": "nishi.sharma@email.com",
        "age": 35,
        "gender": "Female",
        "phone": "9876543211",
        "address": "Delhi, Delhi",
        "medical_history": "Diabetes Type 2",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Nandani Singh",
        "username": "nandani",
        "password": "nandani@123",
        "email": "nandani.singh@email.com",
        "age": 42,
        "gender": "Female",
        "phone": "9876543212",
        "address": "Bangalore, Karnataka",
        "medical_history": "Hypertension",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Lovedeep Kaur",
        "username": "lovedeep",
        "password": "lovedeep@123",
        "email": "lovedeep.kaur@email.com",
        "age": 31,
        "gender": "Female",
        "phone": "9876543213",
        "address": "Punjab, Chandigarh",
        "medical_history": "Migraine",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Rajesh Kumar",
        "username": "rajesh",
        "password": "rajesh@123",
        "email": "rajesh.kumar@email.com",
        "age": 45,
        "gender": "Male",
        "phone": "9876543214",
        "address": "Chennai, Tamil Nadu",
        "medical_history": "None",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Anjali Verma",
        "username": "anjali",
        "password": "anjali@123",
        "email": "anjali.verma@email.com",
        "age": 26,
        "gender": "Female",
        "phone": "9876543215",
        "address": "Hyderabad, Telangana",
        "medical_history": "Asthma",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Vikram Singh",
        "username": "vikram",
        "password": "vikram@123",
        "email": "vikram.singh@email.com",
        "age": 52,
        "gender": "Male",
        "phone": "9876543216",
        "address": "Jaipur, Rajasthan",
        "medical_history": "Heart condition",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Deepika Reddy",
        "username": "deepika",
        "password": "deepika@123",
        "email": "deepika.reddy@email.com",
        "age": 33,
        "gender": "Female",
        "phone": "9876543217",
        "address": "Kolkata, West Bengal",
        "medical_history": "None",
        "created_at": datetime.utcnow()
    }
]
patients_col.insert_many(patients)
print(f"✓ Added {len(patients)} patients")

# ==================== DOCTOR DATA ====================
print("Adding Doctor data...")
doctors = [
    {
        "name": "Dr. Arun Mishra",
        "username": "dr_arun",
        "password": "arun@123",
        "department": "Cardiology",
        "email": "arun.mishra@hospital.com",
        "phone": "9888000001",
        "experience": "15 years",
        "qualification": "MBBS, MD Cardiology",
        "specialization": "Heart Diseases",
        "status_override": "available",
        "leave_dates": [],
        "break_start": "13:00",
        "break_end": "14:00",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Dr. Meera Chatterjee",
        "username": "dr_meera",
        "password": "meera@123",
        "department": "Pediatrics",
        "email": "meera.chatterjee@hospital.com",
        "phone": "9888000002",
        "experience": "12 years",
        "qualification": "MBBS, MD Pediatrics",
        "specialization": "Child Health",
        "status_override": "available",
        "leave_dates": [],
        "break_start": "13:00",
        "break_end": "14:00",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Dr. Suresh Nair",
        "username": "dr_suresh",
        "password": "suresh@123",
        "department": "General Medicine",
        "email": "suresh.nair@hospital.com",
        "phone": "9888000003",
        "experience": "18 years",
        "qualification": "MBBS, MD General Medicine",
        "specialization": "General Diseases",
        "status_override": "available",
        "leave_dates": [],
        "break_start": "13:00",
        "break_end": "14:00",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Dr. Priya Gupta",
        "username": "dr_priya",
        "password": "priya@123",
        "department": "Orthopedics",
        "email": "priya.gupta@hospital.com",
        "phone": "9888000004",
        "experience": "10 years",
        "qualification": "MBBS, MS Orthopedics",
        "specialization": "Bone & Joint",
        "status_override": "available",
        "leave_dates": [],
        "break_start": "13:00",
        "break_end": "14:00",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Dr. Rajiv Saxena",
        "username": "dr_rajiv",
        "password": "rajiv@123",
        "department": "Neurology",
        "email": "rajiv.saxena@hospital.com",
        "phone": "9888000005",
        "experience": "16 years",
        "qualification": "MBBS, MD Neurology",
        "specialization": "Brain & Nervous System",
        "status_override": "available",
        "leave_dates": [],
        "break_start": "13:00",
        "break_end": "14:00",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Dr. Ananya Desai",
        "username": "dr_ananya",
        "password": "ananya@123",
        "department": "Dermatology",
        "email": "ananya.desai@hospital.com",
        "phone": "9888000006",
        "experience": "8 years",
        "qualification": "MBBS, MD Dermatology",
        "specialization": "Skin Diseases",
        "status_override": "available",
        "leave_dates": [],
        "break_start": "13:00",
        "break_end": "14:00",
        "created_at": datetime.utcnow()
    }
]
doctors_col.insert_many(doctors)
print(f"✓ Added {len(doctors)} doctors")

# ==================== STAFF DATA ====================
print("Adding Staff data...")
staff = [
    {
        "name": "Sunil Kumar",
        "username": "staff_sunil",
        "password": "sunil@123",
        "role": "Receptionist",
        "email": "sunil@hospital.com",
        "phone": "9877000001",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Kavya Iyer",
        "username": "staff_kavya",
        "password": "kavya@123",
        "role": "Nurse",
        "email": "kavya@hospital.com",
        "phone": "9877000002",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Prakash Rao",
        "username": "staff_prakash",
        "password": "prakash@123",
        "role": "Lab Technician",
        "email": "prakash@hospital.com",
        "phone": "9877000003",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Neha Malik",
        "username": "staff_neha",
        "password": "neha@123",
        "role": "Pharmacist",
        "email": "neha@hospital.com",
        "phone": "9877000004",
        "created_at": datetime.utcnow()
    },
    {
        "name": "Arjun Mehta",
        "username": "staff_arjun",
        "password": "arjun@123",
        "role": "Nurse",
        "email": "arjun@hospital.com",
        "phone": "9877000005",
        "created_at": datetime.utcnow()
    }
]
staff_col.insert_many(staff)
print(f"✓ Added {len(staff)} staff members")

# ==================== HOSPITAL DATA ====================
print("Adding Hospital data...")
hospitals = [
    {"name": "Ever Well Hospital",        "disease": "Cardiology",       "specialty": "Cardiology",       "distance": "1.2 km"},
    {"name": "Ever Well Hospital",        "disease": "Cardiac",          "specialty": "Cardiology",       "distance": "1.2 km"},
    {"name": "Ever Well Hospital",        "disease": "Heart",            "specialty": "Cardiology",       "distance": "1.2 km"},
    {"name": "Apollo Children's Hospital", "disease": "Pediatrics",       "specialty": "Pediatrics",       "distance": "2.5 km"},
    {"name": "Apollo Children's Hospital", "disease": "Child",            "specialty": "Pediatrics",       "distance": "2.5 km"},
    {"name": "Central Medical Centre",     "disease": "General Medicine", "specialty": "General Medicine", "distance": "0.8 km"},
    {"name": "Central Medical Centre",     "disease": "Fever",            "specialty": "General Medicine", "distance": "0.8 km"},
    {"name": "Central Medical Centre",     "disease": "Cold",             "specialty": "General Medicine", "distance": "0.8 km"},
    {"name": "OrthoPlus Hospital",         "disease": "Orthopedics",      "specialty": "Orthopedics",      "distance": "3.1 km"},
    {"name": "OrthoPlus Hospital",         "disease": "Bone",             "specialty": "Orthopedics",      "distance": "3.1 km"},
    {"name": "OrthoPlus Hospital",         "disease": "Joint",            "specialty": "Orthopedics",      "distance": "3.1 km"},
    {"name": "NeuroLife Hospital",         "disease": "Neurology",        "specialty": "Neurology",        "distance": "4.0 km"},
    {"name": "NeuroLife Hospital",         "disease": "Brain",            "specialty": "Neurology",        "distance": "4.0 km"},
    {"name": "NeuroLife Hospital",         "disease": "Migraine",         "specialty": "Neurology",        "distance": "4.0 km"},
    {"name": "SkinCare Clinic",            "disease": "Dermatology",      "specialty": "Dermatology",      "distance": "1.8 km"},
    {"name": "SkinCare Clinic",            "disease": "Skin",             "specialty": "Dermatology",      "distance": "1.8 km"},
    {"name": "SkinCare Clinic",            "disease": "Allergy",          "specialty": "Dermatology",      "distance": "1.8 km"},
    {"name": "DiabetesCare Centre",        "disease": "Diabetes",         "specialty": "Endocrinology",    "distance": "2.2 km"},
    {"name": "DiabetesCare Centre",        "disease": "Endocrinology",    "specialty": "Endocrinology",    "distance": "2.2 km"},
    {"name": "LungCare Hospital",          "disease": "Pulmonology",      "specialty": "Pulmonology",      "distance": "3.5 km"},
    {"name": "LungCare Hospital",          "disease": "Asthma",           "specialty": "Pulmonology",      "distance": "3.5 km"},
    {"name": "LungCare Hospital",          "disease": "Respiratory",      "specialty": "Pulmonology",      "distance": "3.5 km"},
    {"name": "EyeCare Vision Hospital",    "disease": "Ophthalmology",    "specialty": "Ophthalmology",    "distance": "2.9 km"},
    {"name": "EyeCare Vision Hospital",    "disease": "Eye",              "specialty": "Ophthalmology",    "distance": "2.9 km"},
    {"name": "DentaSmile Clinic",          "disease": "Dentistry",        "specialty": "Dentistry",        "distance": "1.5 km"},
    {"name": "DentaSmile Clinic",          "disease": "Dental",           "specialty": "Dentistry",        "distance": "1.5 km"},
    {"name": "WomenCare Hospital",         "disease": "Gynecology",       "specialty": "Gynecology",       "distance": "2.0 km"},
    {"name": "WomenCare Hospital",         "disease": "Obstetrics",       "specialty": "Gynecology",       "distance": "2.0 km"},
    {"name": "ENT Specialist Centre",      "disease": "ENT",              "specialty": "ENT",              "distance": "1.6 km"},
    {"name": "ENT Specialist Centre",      "disease": "Ear",              "specialty": "ENT",              "distance": "1.6 km"},
    {"name": "ENT Specialist Centre",      "disease": "Throat",           "specialty": "ENT",              "distance": "1.6 km"},
    {"name": "PsycheCare Hospital",        "disease": "Psychiatry",       "specialty": "Psychiatry",       "distance": "5.0 km"},
    {"name": "PsycheCare Hospital",        "disease": "Mental Health",    "specialty": "Psychiatry",       "distance": "5.0 km"},
    {"name": "KidneyCare Hospital",        "disease": "Nephrology",       "specialty": "Nephrology",       "distance": "3.8 km"},
    {"name": "KidneyCare Hospital",        "disease": "Kidney",           "specialty": "Nephrology",       "distance": "3.8 km"},
    {"name": "GastroHealth Centre",        "disease": "Gastroenterology", "specialty": "Gastroenterology", "distance": "2.7 km"},
    {"name": "GastroHealth Centre",        "disease": "Stomach",          "specialty": "Gastroenterology", "distance": "2.7 km"},
    {"name": "GastroHealth Centre",        "disease": "Liver",            "specialty": "Gastroenterology", "distance": "2.7 km"},
]
hospitals_col.insert_many(hospitals)

# ==================== APPOINTMENTS DATA ====================
print("Adding Appointment data...")
appointments = [
    {
        "username": "hitu",
        "patient_name": "Hitu Patel",
        "doctor": "Dr. Meera Chatterjee",
        "department": "Pediatrics",
        "date": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
        "time": "10:00",
        "reason": "Regular checkup",
        "status": "Confirmed",
        "token_no": "T001",
        "created_at": datetime.utcnow(),
        "history": False
    },
    {
        "username": "nishi",
        "patient_name": "Nishi Sharma",
        "doctor": "Dr. Arun Mishra",
        "department": "Cardiology",
        "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "time": "14:30",
        "reason": "Heart checkup",
        "status": "Confirmed",
        "token_no": "T002",
        "created_at": datetime.utcnow(),
        "history": False
    },
    {
        "username": "nandani",
        "patient_name": "Nandani Singh",
        "doctor": "Dr. Suresh Nair",
        "department": "General Medicine",
        "date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
        "time": "11:00",
        "reason": "Blood pressure monitoring",
        "status": "Confirmed",
        "token_no": "T003",
        "created_at": datetime.utcnow(),
        "history": False
    },
    {
        "username": "lovedeep",
        "patient_name": "Lovedeep Kaur",
        "doctor": "Dr. Rajiv Saxena",
        "department": "Neurology",
        "date": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d"),
        "time": "15:00",
        "reason": "Migraine consultation",
        "status": "Confirmed",
        "token_no": "T004",
        "created_at": datetime.utcnow(),
        "history": False
    },
    {
        "username": "rajesh",
        "patient_name": "Rajesh Kumar",
        "doctor": "Dr. Priya Gupta",
        "department": "Orthopedics",
        "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "time": "09:00",
        "reason": "Back pain",
        "status": "Completed",
        "token_no": "T005",
        "created_at": datetime.utcnow(),
        "history": True
    }
]
appointments_col.insert_many(appointments)
print(f"✓ Added {len(appointments)} appointments")

# ==================== PRESCRIPTIONS DATA ====================
print("Adding Prescriptions data...")
prescriptions = [
    {
        "patient_username": "hitu",
        "patient_name": "Hitu Patel",
        "doctor": "Dr. Meera Chatterjee",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "medicines": "Calpol 500mg\nParacetamol 650mg\nVitamin C",
        "instructions": "Twice daily after meals",
        "created_at": datetime.utcnow()
    },
    {
        "patient_username": "nishi",
        "patient_name": "Nishi Sharma",
        "doctor": "Dr. Arun Mishra",
        "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
        "medicines": "Aspirin 100mg\nLisinopril 10mg\nAtorvastin 20mg",
        "instructions": "Once daily in the morning",
        "created_at": datetime.utcnow()
    },
    {
        "patient_username": "nandani",
        "patient_name": "Nandani Singh",
        "doctor": "Dr. Suresh Nair",
        "date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        "medicines": "Amlodipine 5mg\nHydrochlorothiazide 25mg",
        "instructions": "Once daily in the evening",
        "created_at": datetime.utcnow()
    }
]
prescriptions_col.insert_many(prescriptions)
print(f"✓ Added {len(prescriptions)} prescriptions")

# ==================== RATINGS DATA ====================
print("Adding Ratings data...")
ratings = [
    {
        "patient_username": "hitu",
        "doctor": "Dr. Meera Chatterjee",
        "date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "rating": 5,
        "review": "Excellent doctor, very caring and professional",
        "submitted_at": datetime.utcnow()
    },
    {
        "patient_username": "nishi",
        "doctor": "Dr. Arun Mishra",
        "date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
        "rating": 4,
        "review": "Good doctor, clear explanation about treatment",
        "submitted_at": datetime.utcnow()
    },
    {
        "patient_username": "rajesh",
        "doctor": "Dr. Priya Gupta",
        "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
        "rating": 5,
        "review": "Best orthopedic doctor, pain relief was immediate",
        "submitted_at": datetime.utcnow()
    }
]
ratings_col.insert_many(ratings)
print(f"✓ Added {len(ratings)} ratings")

print("\n" + "="*50)
print("✅ DATABASE SETUP COMPLETED SUCCESSFULLY!")
print("="*50)
print("\nTest Credentials:")
print("\n📋 ADMIN:")
print("  Username: admin | Password: admin123")
print("  Username: admin2 | Password: admin123")
print("\n👥 PATIENTS:")
print("  Username: hitu | Password: hitu@123")
print("  Username: nishi | Password: nishi@123")
print("  Username: nandani | Password: nandani@123")
print("  Username: lovedeep | Password: lovedeep@123")
print("  Username: rajesh | Password: rajesh@123")
print("  Username: anjali | Password: anjali@123")
print("  Username: vikram | Password: vikram@123")
print("  Username: deepika | Password: deepika@123")
print("\n👨‍⚕️ DOCTORS:")
print("  Username: dr_arun | Password: arun@123")
print("  Username: dr_meera | Password: meera@123")
print("  Username: dr_suresh | Password: suresh@123")
print("  Username: dr_priya | Password: priya@123")
print("  Username: dr_rajiv | Password: rajiv@123")
print("  Username: dr_ananya | Password: ananya@123")
print("\n👔 STAFF:")
print("  Username: staff_sunil | Password: sunil@123")
print("  Username: staff_kavya | Password: kavya@123")
print("  Username: staff_prakash | Password: prakash@123")
print("  Username: staff_neha | Password: neha@123")
print("  Username: staff_arjun | Password: arjun@123")
print("="*50 + "\n")
