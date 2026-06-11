# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, make_response
from datetime import datetime, timedelta
from bson.objectid import ObjectId
import io
import os
from dotenv import load_dotenv
load_dotenv()

# ── ReportLab for on-the-fly PDF generation ──────────────────────────────────
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from db import (
    patients_col,
    doctors_col,
    staff_col,
    admin_col,
    appointments_col,
    hospitals_col,
    prescriptions_col,
    ratings_col
)
from reminders import start_reminder_scheduler

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-fallback-change-in-prod")

# Start scheduler when running under gunicorn or directly
if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    import logging
    logging.basicConfig(level=logging.INFO)
    from reminders import start_reminder_scheduler
    from db import appointments_col, patients_col as _patients_col
    start_reminder_scheduler(appointments_col, _patients_col)

# ─────────────────────────────────────────────────────────────────────────────
# Session config — 30 minute inactivity timeout
# ─────────────────────────────────────────────────────────────────────────────
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

SESSION_TIMEOUT = timedelta(minutes=30)

@app.before_request
def check_session_timeout():
    # Skip static files, PWA assets, and the login/register routes
    open_routes = {"login", "register", "static", "service_worker", "manifest"}
    if request.endpoint in open_routes:
        return

    # If not logged in, redirect to login
    if "username" not in session:
        flash("Please log in to continue.", "error")
        return redirect(url_for("login"))

    # Check inactivity timeout
    last_active = session.get("last_active")
    if last_active:
        last_active_dt = datetime.fromisoformat(last_active)
        if datetime.utcnow() - last_active_dt > SESSION_TIMEOUT:
            session.clear()
            flash("⏰ Your session expired due to inactivity. Please log in again.", "warning")
            return redirect(url_for("login"))

    # Update last active timestamp on every request
    session["last_active"] = datetime.utcnow().isoformat()
    session.permanent = True

# ─────────────────────────────────────────────────────────────────────────────
# Helper: get doctor leave/status doc
# ─────────────────────────────────────────────────────────────────────────────
def get_doctor_status(doctor_name):
    doc = doctors_col.find_one(
        {"name": {"$regex": f"^{doctor_name}$", "$options": "i"}},
        {"leave_dates": 1, "break_start": 1, "break_end": 1, "status_override": 1}
    )
    if not doc:
        return {"status": "available", "leave_dates": [], "break_start": "13:00", "break_end": "14:00", "message": ""}

    leave_dates     = doc.get("leave_dates",    [])
    break_start     = doc.get("break_start",    "13:00")
    break_end       = doc.get("break_end",      "14:00")
    status_override = doc.get("status_override", "available")

    today_str = datetime.now().strftime("%Y-%m-%d")
    now_time  = datetime.now().strftime("%H:%M")

    if status_override == "offline":
        return {
            "status": "offline",
            "leave_dates": leave_dates,
            "break_start": break_start,
            "break_end":   break_end,
            "message": "Doctor is currently offline / not logged in."
        }

    if today_str in leave_dates:
        return {
            "status": "on_leave",
            "leave_dates": leave_dates,
            "break_start": break_start,
            "break_end":   break_end,
            "message": f"Doctor is on leave today ({today_str}). Please choose another date."
        }

    if break_start <= now_time < break_end:
        return {
            "status": "on_break",
            "leave_dates": leave_dates,
            "break_start": break_start,
            "break_end":   break_end,
            "message": f"Doctor is on lunch break ({break_start}–{break_end}). Choose a time after {break_end}."
        }

    return {
        "status": "available",
        "leave_dates": leave_dates,
        "break_start": break_start,
        "break_end":   break_end,
        "message": ""
    }


# ================= AUTO CLEANUP =================
def auto_cleanup_appointments(username):
    expiry_time = datetime.utcnow() - timedelta(hours=24)
    expired = list(appointments_col.find({
        "username": username,
        "created_at": {"$lt": expiry_time},
        "history": {"$ne": True}
    }))
    for a in expired:
        appointments_col.update_one(
            {"_id": a["_id"]},
            {"$set": {"history": True}}
        )


# ================= HOME =================
@app.route("/")
def home():
    return redirect("/login")

# ================= SERVICE WORKER =================
@app.route("/sw.js")
def service_worker():
    from flask import send_from_directory
    response = send_from_directory("static", "sw.js")
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Service-Worker-Allowed"] = "/"
    return response

@app.route("/manifest.json")
def manifest():
    from flask import send_from_directory
    return send_from_directory("static", "manifest.json")


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role     = request.form.get("role")
        username = request.form.get("username")
        password = request.form.get("password")

        collections = {
            "patient": patients_col,
            "doctor":  doctors_col,
            "staff":   staff_col,
            "admin":   admin_col
        }

        user = collections.get(role).find_one({
            "username": username.strip(),
            "password": password.strip()
        })

        if not user:
            flash("Invalid credentials", "error")
            return redirect("/login")

        session["username"] = username
        session["role"]     = role
        session["last_active"] = datetime.utcnow().isoformat()
        session.permanent  = True

        if role == "patient": return redirect(url_for("patient_dashboard", username=username))
        if role == "doctor":  return redirect(url_for("doctor_dashboard",  username=username))
        if role == "staff":   return redirect("/staff")
        if role == "admin":   return redirect("/admin")

    return render_template("login.html")


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        patients_col.insert_one({
            "name":     request.form["name"],
            "username": request.form["username"],
            "password": request.form["password"]
        })
        flash("Registration successful", "success")
        return redirect("/login")
    return render_template("register.html")


# ================= UPDATE PATIENT PROFILE =================
@app.route("/patient/update-profile", methods=["POST"])
def update_patient_profile():
    username = request.form.get("username", "").strip()
    mobile   = request.form.get("mobile",   "").strip()
    email    = request.form.get("email",    "").strip()
    age      = request.form.get("age",      "").strip()
    gender   = request.form.get("gender",   "").strip()
    address   = request.form.get("address",   "").strip()
    blood     = request.form.get("blood",     "").strip()
    height    = request.form.get("height",    "").strip()
    weight    = request.form.get("weight",    "").strip()
    allergies = request.form.get("allergies", "").strip()

    if not username:
        flash("❌ Invalid request.", "error")
        return redirect("/login")

    # Validate mobile number
    import re
    if mobile and not re.match(r'^[6-9]\d{9}$', mobile):
        flash("❌ Invalid mobile number. Must be 10 digits starting with 6, 7, 8, or 9.", "error")
        return redirect(url_for("patient_dashboard", username=username))

    # Validate email format
    if email and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$', email):
        flash("❌ Invalid email address. Please enter a valid email like name@gmail.com", "error")
        return redirect(url_for("patient_dashboard", username=username))

    update_data = {}
    if mobile:     update_data["mobile"]    = mobile
    if email:      update_data["email"]     = email
    if age:        update_data["age"]       = age
    if gender:     update_data["gender"]    = gender
    if address:    update_data["address"]   = address
    if blood:      update_data["blood"]     = blood
    if height:     update_data["height"]    = height
    if weight:     update_data["weight"]    = weight
    if allergies:  update_data["allergies"] = allergies

    if update_data:
        patients_col.update_one(
            {"username": username},
            {"$set": update_data}
        )
        flash("✅ Profile updated successfully!", "success")
    else:
        flash("⚠️ No changes made.", "warning")

    return redirect(url_for("patient_dashboard", username=username))


# ================= PATIENT DASHBOARD =================
@app.route("/patient/<username>")
def patient_dashboard(username):
    auto_cleanup_appointments(username)

    patient = patients_col.find_one({"username": username})

    appointments = list(appointments_col.find({
        "username": username,
        "history":  {"$ne": True},
        "status":   {"$ne": "Cancelled"}
    }))
    for a in appointments:
        a["_id"] = str(a["_id"])

    history = list(appointments_col.find({
        "username": username,
        "history":  True
    }))
    for h in history:
        h["_id"] = str(h["_id"])

    raw_prescriptions = list(
        prescriptions_col.find({"patient_username": username}).sort("created_at", -1)
    )

    prescriptions = []
    for i, p in enumerate(raw_prescriptions):
        meds_raw = p.get("medicines", "")
        if isinstance(meds_raw, list):
            med_list = meds_raw
        else:
            lines = meds_raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            med_list = []
            for line in lines:
                for part in line.split(","):
                    part = part.strip()
                    if part:
                        med_list.append(part)

        prescriptions.append({
            "id":          str(p["_id"]),
            "serial":      i + 1,
            "doctor":      p.get("doctor", ""),
            "date":        p.get("date",   ""),
            "medications": med_list,
            "notes":       p.get("notes",  ""),
            "file_url":    f"/download-prescription/{str(p['_id'])}"
        })

    patient_ratings = list(ratings_col.find({"patient_username": username}))
    reviewed_appointment_ids = set(
        str(r["appointment_id"]) for r in patient_ratings if r.get("appointment_id")
    )

    doctors_raw = list(doctors_col.find({}, {"_id": 0, "name": 1, "department": 1,
                                              "leave_dates": 1, "break_start": 1,
                                              "break_end": 1, "status_override": 1}).sort("name", 1))

    doctors = []
    for d in doctors_raw:
        st = get_doctor_status(d["name"])
        doctors.append({
            "name":         d["name"],
            "department":   d["department"],
            "leave_dates":  st["leave_dates"],
            "break_start":  st["break_start"],
            "break_end":    st["break_end"],
            "status":       st["status"],
            "status_msg":   st["message"]
        })

    # Bills sent by staff
    bills_col = prescriptions_col.database["bills"]
    raw_bills = list(bills_col.find(
        {"patient_username": username},
        sort=[("created_at", -1)]
    ))
    bills = []
    for b in raw_bills:
        bills.append({
            "id":                   str(b["_id"]),
            "doctor":               b.get("doctor", ""),
            "date":                 b.get("created_at", "").strftime("%Y-%m-%d") if b.get("created_at") else "",
            "line_items":           b.get("line_items", []),
            "total_amount":         b.get("total_amount", 0),
            "status":               b.get("status", "sent"),
            "notes":                b.get("notes", ""),
            "payment_screenshot":   b.get("payment_screenshot", ""),
        })

    return render_template(
        "patient_dashboard.html",
        patient=patient,
        appointments=appointments,
        history=history,
        medical_reports=[],
        prescriptions=prescriptions,
        reviewed_appointment_ids=reviewed_appointment_ids,
        doctors=doctors,
        bills=bills
    )


# ================= API: DOCTOR STATUS =================
@app.route("/api/doctor-status/<doctor_name>")
def api_doctor_status(doctor_name):
    return jsonify(get_doctor_status(doctor_name))


# ================= LIVE STATUS API — PATIENT =================
@app.route("/api/patient-appointments/<username>")
def api_patient_appointments(username):
    all_appointments = list(appointments_col.find({"username": username}))
    result = []
    for a in all_appointments:
        result.append({
            "id":      str(a["_id"]),
            "doctor":  a.get("doctor",  ""),
            "date":    a.get("date",    ""),
            "time":    a.get("time",    ""),
            "status":  a.get("status",  "Booked"),
            "history": a.get("history", False),
            "token":   a.get("token",   0)
        })
    return jsonify({"appointments": result})


# ================= API: DOCTOR APPOINTMENTS =================
@app.route("/api/doctor-appointments/<username>")
def api_doctor_appointments(username):
    doctor = doctors_col.find_one({"username": username})
    if not doctor:
        return jsonify({"appointments": []})

    today_date = datetime.now().strftime("%Y-%m-%d")

    all_appts = list(appointments_col.find({
        "$or": [
            {"doctor": {"$regex": f"^{doctor['name']}$",     "$options": "i"}},
            {"doctor": {"$regex": f"^{doctor['username']}$", "$options": "i"}}
        ],
        "date": today_date
    }).sort("created_at", 1))

    result = []
    for a in all_appts:
        result.append({
            "_id":      str(a["_id"]),
            "id":       str(a["_id"]),
            "username": a.get("username", ""),
            "doctor":   a.get("doctor",   ""),
            "date":     a.get("date",     ""),
            "time":     a.get("time",     ""),
            "status":   a.get("status",   "Booked"),
            "token":    a.get("token",    0),
            "history":  a.get("history",  False)
        })

    return jsonify({"appointments": result})


# ================= DELETE HISTORY =================
@app.route("/delete-history", methods=["POST"])
def delete_history():
    appointment_id = request.form.get("appointment_id")
    if not appointment_id:
        return jsonify({"status": "error", "message": "No appointment_id provided"}), 400
    try:
        result = appointments_col.delete_one({"_id": ObjectId(appointment_id)})
        if result.deleted_count == 0:
            return jsonify({"status": "error", "message": "Appointment not found"}), 404
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ================= BOOK APPOINTMENT =================
@app.route("/book-appointment", methods=["POST"])
def book_appointment():
    username = request.form["username"]
    doctor   = request.form["doctor"]
    date     = request.form["date"]
    time     = request.form["time"]

    # ── Profile completeness check ──
    patient = patients_col.find_one({"username": username})
    if not patient:
        flash("❌ Patient not found.", "error")
        return redirect(url_for("patient_dashboard", username=username))

    missing = []
    if not patient.get("mobile"):  missing.append("mobile number")
    if not patient.get("email"):   missing.append("email")
    if not patient.get("age"):     missing.append("age")
    if missing:
        flash(
            f"⚠️ Please complete your profile before booking. Missing: {', '.join(missing)}.",
            "error"
        )
        return redirect(url_for("patient_dashboard", username=username))

    hour, minute = map(int, time.split(":"))

    if hour < 9 or hour >= 21:
        flash("⏰ Appointments allowed only between 09:00 AM and 09:00 PM", "error")
        return redirect(url_for("patient_dashboard", username=username))

    doc_info = doctors_col.find_one(
        {"name": {"$regex": f"^{doctor}$", "$options": "i"}},
        {"leave_dates": 1, "break_start": 1, "break_end": 1, "status_override": 1}
    ) or {}

    leave_dates     = doc_info.get("leave_dates",     [])
    break_start_str = doc_info.get("break_start",     "13:00")
    break_end_str   = doc_info.get("break_end",       "14:00")
    status_override = doc_info.get("status_override", "available")

    if status_override == "offline":
        flash(f"❌ Dr. {doctor} is currently offline / not available for booking.", "error")
        return redirect(url_for("patient_dashboard", username=username))

    if date in leave_dates:
        flash(f"🏖️ Dr. {doctor} is on leave on {date}. Please choose a different date.", "error")
        return redirect(url_for("patient_dashboard", username=username))

    today_str = datetime.now().strftime("%Y-%m-%d")
    if date == today_str:
        appt_time_str = f"{hour:02d}:{minute:02d}"
        if break_start_str <= appt_time_str < break_end_str:
            flash(
                f"⏸️ Dr. {doctor} is on lunch break {break_start_str}–{break_end_str}. "
                f"Please choose a time after {break_end_str}.",
                "error"
            )
            return redirect(url_for("patient_dashboard", username=username))

    count    = appointments_col.count_documents({"doctor": doctor, "date": date})
    token    = count + 1
    avg_wait = f"{token * 8} mins"

    appointments_col.insert_one({
        "username":   username,
        "doctor":     doctor,
        "date":       date,
        "time":       time,
        "hospital":   "Ever Well Hospital",
        "token":      token,
        "avg_wait":   avg_wait,
        "status":     "Booked",
        "message":    "Appointment booked successfully",
        "created_at": datetime.utcnow(),
        "history":    False
    })

    flash("✅ Appointment booked successfully!", "success")
    return redirect(url_for("patient_dashboard", username=username))


# ================= CANCEL APPOINTMENT =================
@app.route("/cancel-appointment", methods=["POST"])
def cancel_appointment():
    appointment_id = request.form.get("appointment_id")
    appointment    = appointments_col.find_one({"_id": ObjectId(appointment_id)})

    if not appointment:
        flash("Appointment not found", "error")
        return redirect(request.referrer)

    appointments_col.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {"status": "Cancelled", "history": True}}
    )

    flash("Appointment cancelled successfully", "success")
    return redirect(url_for("patient_dashboard", username=appointment["username"]))


# ================= RESCHEDULE APPOINTMENT =================
@app.route("/reschedule-appointment", methods=["POST"])
def reschedule_appointment():
    appointment_id = request.form.get("appointment_id")
    new_date       = request.form.get("date")
    new_time       = request.form.get("time")

    old = appointments_col.find_one({"_id": ObjectId(appointment_id)})

    if not old:
        flash("Appointment not found", "error")
        return redirect(request.referrer)

    hour, minute = map(int, new_time.split(":"))

    if hour < 9 or hour >= 21:
        flash("⏰ Appointments allowed only between 09:00 AM and 09:00 PM", "error")
        return redirect(url_for("patient_dashboard", username=old["username"]))

    appointments_col.insert_one({
        "username":   old["username"],
        "doctor":     old["doctor"],
        "date":       new_date,
        "time":       new_time,
        "hospital":   old.get("hospital", ""),
        "token":      old["token"],
        "avg_wait":   old["avg_wait"],
        "status":     "Rescheduled",
        "message":    "Appointment rescheduled by patient",
        "created_at": datetime.utcnow(),
        "history":    False
    })

    appointments_col.update_one(
        {"_id": old["_id"]},
        {"$set": {"history": True}}
    )

    flash("Appointment rescheduled successfully", "success")
    return redirect(url_for("patient_dashboard", username=old["username"]))


# ================= DELETE REVIEW =================
@app.route("/delete_review/<appointment_id>", methods=["POST"])
def delete_review(appointment_id):
    appointment = appointments_col.find_one({"_id": ObjectId(appointment_id)})
    if not appointment:
        flash("Appointment not found!", "danger")
        return redirect(request.referrer)
    if appointment.get("status") != "Completed":
        flash("Review can only be deleted after completed appointment.", "warning")
        return redirect(url_for("patient_dashboard", username=appointment["username"]))
    appointments_col.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$unset": {"review": "", "rating": ""}}
    )
    ratings_col.delete_one({"appointment_id": ObjectId(appointment_id)})
    flash("Review deleted successfully!", "success")
    return redirect(url_for("patient_dashboard", username=appointment["username"]))


# ================= SUBMIT REVIEW =================
@app.route("/submit-review", methods=["POST"])
def submit_review():
    appointment_id = request.form["appointment_id"]
    rating         = int(request.form["rating"])
    review         = request.form["review"]

    appointment = appointments_col.find_one({"_id": ObjectId(appointment_id)})
    if not appointment:
        flash("Appointment not found!", "danger")
        return redirect(request.referrer)

    if appointment.get("status") != "Completed":
        flash("⚠️ Reviews can only be submitted for Completed appointments.", "warning")
        return redirect(url_for("patient_dashboard", username=appointment["username"]))

    username = appointment["username"]
    doctor   = appointment.get("doctor", "")
    date     = appointment.get("date", "")

    appointments_col.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {"rating": rating, "review": review}}
    )
    ratings_col.update_one(
        {"appointment_id": ObjectId(appointment_id)},
        {"$set": {
            "appointment_id":   ObjectId(appointment_id),
            "patient_username": username,
            "doctor":           doctor,
            "date":             date,
            "rating":           rating,
            "review":           review,
            "submitted_at":     datetime.utcnow()
        }},
        upsert=True
    )

    flash("✅ Review submitted successfully! Thank you for your feedback.", "success")
    return redirect(url_for("patient_dashboard", username=username))


# ================= ADD REVIEW (legacy) =================
@app.route("/add-review", methods=["POST"])
def add_review():
    appointment_id = request.form["appointment_id"]
    rating         = int(request.form["rating"])
    review         = request.form["review"]

    appointment = appointments_col.find_one({"_id": ObjectId(appointment_id)})
    if not appointment:
        flash("Appointment not found!", "danger")
        return redirect(request.referrer)

    username = appointment["username"]
    if appointment.get("status") != "Completed":
        flash("Review allowed only after appointment completion.", "warning")
        return redirect(url_for("patient_dashboard", username=username))

    doctor = appointment.get("doctor", "")
    date   = appointment.get("date", "")

    appointments_col.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {"rating": rating, "review": review}}
    )
    ratings_col.update_one(
        {"appointment_id": ObjectId(appointment_id)},
        {"$set": {
            "appointment_id":   ObjectId(appointment_id),
            "patient_username": username,
            "doctor":           doctor,
            "date":             date,
            "rating":           rating,
            "review":           review,
            "submitted_at":     datetime.utcnow()
        }},
        upsert=True
    )

    flash("Review submitted successfully!", "success")
    return redirect(url_for("patient_dashboard", username=username))


# ================= API: GET DOCTOR RATINGS =================
@app.route("/api/doctor-ratings/<doctor_name>")
def api_doctor_ratings(doctor_name):
    all_ratings = list(ratings_col.find(
        {"doctor": {"$regex": f"^{doctor_name}$", "$options": "i"}},
        {"_id": 0, "appointment_id": 0}
    ).sort("submitted_at", -1))
    avg = 0
    if all_ratings:
        avg = round(sum(r["rating"] for r in all_ratings) / len(all_ratings), 1)
    return jsonify({
        "doctor":         doctor_name,
        "average_rating": avg,
        "total_reviews":  len(all_ratings),
        "ratings":        all_ratings
    })


# ================= STAFF: UPDATE EMERGENCY STATUS =================
@app.route("/staff/emergency/<emg_id>/status", methods=["POST"])
def staff_update_emergency(emg_id):
    if session.get("role") != "staff":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    data       = request.get_json() or {}
    new_status = data.get("status", "").strip()

    if new_status not in ("dispatched", "resolved"):
        return jsonify({"status": "error", "message": "Invalid status"}), 400

    try:
        emg_col = appointments_col.database["ambulance_requests"]
        result  = emg_col.update_one(
            {"_id": ObjectId(emg_id)},
            {"$set": {"status": new_status, "updated_at": datetime.utcnow()}}
        )
        if result.matched_count == 0:
            return jsonify({"status": "error", "message": "Request not found"}), 404
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ================= PATIENT: EMERGENCY REQUEST =================
@app.route("/patient/emergency", methods=["POST"])
def patient_emergency():
    data             = request.get_json() or {}
    patient_username = data.get("patient_username", "").strip()
    patient_name     = data.get("patient_name",     "").strip()
    location         = data.get("location",         "").strip()
    reason           = data.get("reason",           "").strip()

    if not patient_username or not location or not reason:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    emg_col = appointments_col.database["ambulance_requests"]
    emg_col.insert_one({
        "patient_username": patient_username,
        "patient_name":     patient_name,
        "location":         location,
        "reason":           reason,
        "status":           "pending",
        "created_at":       datetime.utcnow()
    })

    return jsonify({"status": "ok"})


# ================= SEARCH HOSPITAL =================
@app.route("/search_hospital", methods=["GET", "POST"])
def search_hospital():
    disease = (request.args if request.method == "GET" else request.form).get("disease", "").strip()
    if not disease:
        return jsonify({"status": "fail", "message": "Please enter a disease or specialty"})
    try:
        hospital = hospitals_col.find_one(
            {"disease": {"$regex": disease, "$options": "i"}},
            {"_id": 0}
        )
        if not hospital:
            return jsonify({"status": "fail", "message": f"No hospital found for '{disease}'"})
        return jsonify({
            "status": "ok",
            "hospital": {
                "name":        hospital.get("name",     "Unknown Hospital"),
                "specialty":   hospital.get("disease",  "Unknown Specialty"),
                "distance_km": hospital.get("distance", "N/A")
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"})


# ================= SEARCH PATIENT USERNAME =================
@app.route("/search_patient_username", methods=["POST"])
def search_patient_username():
    username = request.form.get("username", "").strip()
    patient  = patients_col.find_one({"username": username})
    if not patient:
        return jsonify({"status": "not_found"})
    return jsonify({"status": "found", "name": patient.get("name", username)})


# ================= SEND PRESCRIPTION =================
@app.route("/send-prescription", methods=["POST"])
def send_prescription():
    doctor_name      = request.form.get("doctor",           "").strip()
    doctor_username  = request.form.get("doctor_username",  "").strip()
    patient_username = request.form.get("patient_username", "").strip()
    medicines        = request.form.get("medicines",        "").strip()
    notes            = request.form.get("notes",            "").strip()

    if not patient_username:
        flash("⚠️ Please enter the patient's username.", "error")
        return redirect(url_for("doctor_dashboard", username=doctor_username))

    patient = patients_col.find_one({"username": patient_username})
    if not patient:
        flash(f"❌ No patient found with username '{patient_username}'.", "error")
        return redirect(url_for("doctor_dashboard", username=doctor_username))

    if not medicines:
        flash("❌ Medicines & Dosage cannot be empty.", "error")
        return redirect(url_for("doctor_dashboard", username=doctor_username))

    prescriptions_col.insert_one({
        "doctor":           doctor_name,
        "doctor_username":  doctor_username,
        "patient_username": patient_username,
        "patient_name":     patient.get("name", patient_username),
        "medicines":        medicines,
        "notes":            notes,
        "date":             datetime.utcnow().strftime("%Y-%m-%d"),
        "created_at":       datetime.utcnow()
    })

    flash(
        f"✅ Prescription sent successfully to {patient.get('name', patient_username)}!",
        "success"
    )
    return redirect(url_for("doctor_dashboard", username=doctor_username))


# ═══════════════════════════════════════════════════════════════════════════════
# ══  DOCTOR LEAVE / STATUS MANAGEMENT  ══════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/doctor/set-leave", methods=["POST"])
def doctor_set_leave():
    username   = request.form.get("username", "").strip()
    action     = request.form.get("action", "")
    leave_date = request.form.get("leave_date", "").strip()
    break_start= request.form.get("break_start", "").strip()
    break_end  = request.form.get("break_end",   "").strip()
    new_status = request.form.get("status_override", "").strip()

    doctor = doctors_col.find_one({"username": username})
    if not doctor:
        flash("Doctor not found", "error")
        return redirect(url_for("doctor_dashboard", username=username))

    if action == "add_leave" and leave_date:
        doctors_col.update_one(
            {"username": username},
            {"$addToSet": {"leave_dates": leave_date}}
        )
        flash(f"✅ Leave added for {leave_date}", "success")

    elif action == "remove_leave" and leave_date:
        doctors_col.update_one(
            {"username": username},
            {"$pull": {"leave_dates": leave_date}}
        )
        flash(f"🗑️ Leave removed for {leave_date}", "success")

    elif action == "set_break" and break_start and break_end:
        doctors_col.update_one(
            {"username": username},
            {"$set": {"break_start": break_start, "break_end": break_end}}
        )
        flash(f"⏸️ Break time updated: {break_start} – {break_end}", "success")

    elif action == "set_status" and new_status:
        doctors_col.update_one(
            {"username": username},
            {"$set": {"status_override": new_status}}
        )
        label = "🟢 Available" if new_status == "available" else "⭕ Offline"
        flash(f"Status updated to {label}", "success")

    return redirect(url_for("doctor_dashboard", username=username))


@app.route("/doctor/clear-past-leaves", methods=["POST"])
def doctor_clear_past_leaves():
    username = request.form.get("username", "").strip()
    today    = datetime.now().strftime("%Y-%m-%d")

    doctor = doctors_col.find_one({"username": username})
    if not doctor:
        flash("Doctor not found", "error")
        return redirect(url_for("doctor_dashboard", username=username))

    old_leaves   = doctor.get("leave_dates", [])
    fresh_leaves = [d for d in old_leaves if d >= today]

    doctors_col.update_one(
        {"username": username},
        {"$set": {"leave_dates": fresh_leaves}}
    )
    removed = len(old_leaves) - len(fresh_leaves)
    flash(f"🧹 Cleared {removed} past leave date(s).", "success")
    return redirect(url_for("doctor_dashboard", username=username))


# ═══════════════════════════════════════════════════════════════════════════════
# ══  DOWNLOAD PRESCRIPTION PDF  ═════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/download-prescription/<prescription_id>")
def download_prescription(prescription_id):
    try:
        presc = prescriptions_col.find_one({"_id": ObjectId(prescription_id)})
    except Exception:
        flash("Prescription not found.", "error")
        return redirect(request.referrer or "/")

    if not presc:
        flash("Prescription not found.", "error")
        return redirect(request.referrer or "/")

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch,   bottomMargin=0.75*inch
    )
    styles = getSampleStyleSheet()
    story  = []

    purple      = colors.HexColor("#667eea")
    dark_purple = colors.HexColor("#764ba2")
    light_bg    = colors.HexColor("#f5f7ff")
    grid_line   = colors.HexColor("#e0e0e0")
    alt_row     = colors.HexColor("#f0f4ff")
    note_bg     = colors.HexColor("#fffde7")
    note_border = colors.HexColor("#ffe082")

    def ps(name, **kw):
        base = kw.pop("parent", styles["Normal"])
        return ParagraphStyle(name, parent=base, **kw)

    hdr_data = [
        [Paragraph("Medical Prescription", ps("HT",
            fontSize=22, textColor=colors.white,
            alignment=TA_CENTER, fontName="Helvetica-Bold"))],
        [Paragraph("Ever Well Hospital  -  Official Prescription Document", ps("HS",
            fontSize=11, textColor=colors.HexColor("#e8eaf6"),
            alignment=TA_CENTER, fontName="Helvetica"))]
    ]
    hdr = Table(hdr_data, colWidths=[7*inch])
    hdr.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), purple),
        ("ROWPADDING", (0,0), (-1,-1), 14),
    ]))
    story += [hdr, Spacer(1, 20)]

    lbl = ps("LB", fontSize=10, textColor=purple,      fontName="Helvetica-Bold")
    val = ps("VL", fontSize=11, textColor=colors.HexColor("#333"), fontName="Helvetica")

    info = Table([
        [Paragraph("Doctor",     lbl), Paragraph(presc.get("doctor",       "-"), val),
         Paragraph("Patient",    lbl), Paragraph(presc.get("patient_name", presc.get("patient_username","-")), val)],
        [Paragraph("Date",       lbl), Paragraph(presc.get("date",         "-"), val),
         Paragraph("Patient ID", lbl), Paragraph(presc.get("patient_username","-"), val)],
    ], colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
    info.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), light_bg),
        ("GRID",       (0,0), (-1,-1), 0.5, grid_line),
        ("ROWPADDING", (0,0), (-1,-1), 10),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
    ]))
    story += [info, Spacer(1, 18)]

    def section_head(text):
        story.append(Paragraph(text, ps("SH",
            fontSize=13, fontName="Helvetica-Bold",
            textColor=dark_purple, spaceAfter=8)))
        story.append(HRFlowable(width="100%", thickness=1.5,
                                 color=dark_purple, spaceAfter=10))

    section_head("Prescribed Medicines")

    meds_raw = presc.get("medicines", "")
    if isinstance(meds_raw, list):
        med_lines = meds_raw
    else:
        _lines = meds_raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        med_lines = []
        for _line in _lines:
            for _part in _line.split(","):
                _part = _part.strip()
                if _part:
                    med_lines.append(_part)

    if not med_lines:
        med_lines = ["No medicines listed."]

    num_style = ps("NM", fontSize=11, fontName="Helvetica-Bold", textColor=purple)

    for idx, med in enumerate(med_lines, 1):
        row = Table([[Paragraph(f"{idx}.", num_style), Paragraph(med, val)]],
                    colWidths=[0.35*inch, 6.65*inch])
        row.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), alt_row if idx % 2 == 1 else colors.white),
            ("ROWPADDING", (0,0), (-1,-1), 9),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("LINEBELOW",  (0,0), (-1,-1), 0.5, grid_line),
        ]))
        story.append(row)

    story.append(Spacer(1, 18))

    notes_text = presc.get("notes", "").strip()
    if notes_text:
        section_head("Doctor's Notes")
        notes_box = Table([[Paragraph(notes_text, ps("NT",
            fontSize=11, textColor=colors.HexColor("#444"),
            fontName="Helvetica", leading=16))]],
            colWidths=[7*inch])
        notes_box.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,-1), note_bg),
            ("GRID",        (0,0), (-1,-1), 1, note_border),
            ("ROWPADDING",  (0,0), (-1,-1), 14),
            ("LEFTPADDING", (0,0), (-1,-1), 16),
        ]))
        story += [notes_box, Spacer(1, 18)]

    footer = Table([[Paragraph(
        f"Issued by Dr. {presc.get('doctor','')}  |  {presc.get('date','')}  |  Ever Well Hospital",
        ps("FT", fontSize=9, textColor=colors.white,
            alignment=TA_CENTER, fontName="Helvetica")
    )]], colWidths=[7*inch])
    footer.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), dark_purple),
        ("ROWPADDING", (0,0), (-1,-1), 10),
    ]))
    story.append(footer)

    doc.build(story)
    buffer.seek(0)

    fname    = f"prescription_{presc.get('patient_username','patient')}_{presc.get('date','date')}.pdf"
    response = make_response(buffer.read())
    response.headers["Content-Type"]        = "application/pdf"
    response.headers["Content-Disposition"] = f'inline; filename="{fname}"'
    return response


# ================= DOCTOR DASHBOARD =================
@app.route("/doctor/<username>")
def doctor_dashboard(username):
    doctor = doctors_col.find_one({"username": username})
    if not doctor:
        flash("Doctor not found", "error")
        return redirect("/login")

    today_date = datetime.now().strftime("%Y-%m-%d")

    appointments = list(appointments_col.find({
        "$or": [
            {"doctor": {"$regex": f"^{doctor['name']}$",     "$options": "i"}},
            {"doctor": {"$regex": f"^{doctor['username']}$", "$options": "i"}}
        ],
        "date":    today_date,
        "history": {"$ne": True}
    }).sort("token", 1))

    if not appointments:
        appointments = list(appointments_col.find({
            "$or": [
                {"doctor": {"$regex": f"^{doctor['name']}$",     "$options": "i"}},
                {"doctor": {"$regex": f"^{doctor['username']}$", "$options": "i"}}
            ],
            "date": today_date
        }).sort("token", 1))

    # Enrich appointments with patient profile info
    for a in appointments:
        pat = patients_col.find_one(
            {"username": a.get("username", "")},
            {"name": 1, "mobile": 1, "email": 1, "age": 1, "gender": 1, "blood": 1}
        ) or {}
        a["patient_name"]   = pat.get("name",   a.get("username", ""))
        a["patient_mobile"] = pat.get("mobile", "—")
        a["patient_age"]    = pat.get("age",    "—")
        a["patient_gender"] = pat.get("gender", "—")
        a["patient_blood"]  = pat.get("blood",  "—")
        a["_id"]            = str(a["_id"])

    total_appointments     = len(appointments)
    pending_appointments   = len([a for a in appointments if a.get("status") in ["Booked","Rescheduled"]])
    completed_appointments = len([a for a in appointments if a.get("status") == "Completed"])
    total_patients         = len(set(a["username"] for a in appointments)) if appointments else 0
    current_token          = session.get(f"token_{username}", 0)

    doctor_ratings = list(ratings_col.find(
        {"doctor": {"$regex": f"^{doctor['name']}$", "$options": "i"}},
    ).sort("submitted_at", -1))
    avg_rating = 0
    if doctor_ratings:
        avg_rating = round(sum(r["rating"] for r in doctor_ratings) / len(doctor_ratings), 1)

    raw_prescriptions = list(
        prescriptions_col.find({"doctor_username": username}).sort("created_at", -1)
    )

    sent_prescriptions = []
    for i, p in enumerate(raw_prescriptions):
        meds_raw = p.get("medicines", "")
        if isinstance(meds_raw, list):
            med_list = meds_raw
        else:
            lines = meds_raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            med_list = []
            for line in lines:
                for part in line.split(","):
                    part = part.strip()
                    if part:
                        med_list.append(part)

        sent_prescriptions.append({
            "id":               str(p["_id"]),
            "serial":           i + 1,
            "patient_name":     p.get("patient_name", p.get("patient_username", "-")),
            "patient_username": p.get("patient_username", "-"),
            "date":             p.get("date", ""),
            "medications":      med_list,
            "notes":            p.get("notes", ""),
            "file_url":         f"/download-prescription/{str(p['_id'])}"
        })

    leave_dates     = doctor.get("leave_dates",     [])
    break_start     = doctor.get("break_start",     "13:00")
    break_end       = doctor.get("break_end",       "14:00")
    status_override = doctor.get("status_override", "available")

    today = datetime.now().strftime("%Y-%m-%d")
    upcoming_leaves = sorted([d for d in leave_dates if d >= today])
    past_leaves     = sorted([d for d in leave_dates if d < today], reverse=True)

    return render_template(
        "doctor_dashboard.html",
        doctor=doctor,
        appointments=appointments,
        total_appointments=total_appointments,
        pending_appointments=pending_appointments,
        completed_appointments=completed_appointments,
        total_patients=total_patients,
        current_token=current_token,
        sent_prescriptions=sent_prescriptions,
        doctor_ratings=doctor_ratings,
        avg_rating=avg_rating,
        leave_dates=leave_dates,
        upcoming_leaves=upcoming_leaves,
        past_leaves=past_leaves,
        break_start=break_start,
        break_end=break_end,
        status_override=status_override
    )


# ================= NEXT TOKEN =================
@app.route("/doctor/next_token/<username>", methods=["POST"])
def next_token(username):
    now            = datetime.now()
    token_key      = f"token_{username}"
    token_time_key = f"token_time_{username}"
    last_time      = session.get(token_time_key)

    if last_time:
        last_time = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
        if now - last_time > timedelta(hours=24):
            session[token_key] = 0

    today_date = now.strftime("%Y-%m-%d")
    doctor     = doctors_col.find_one({"username": username})

    today_appointments = appointments_col.count_documents({
        "$or": [
            {"doctor": {"$regex": f"^{doctor['name']}$",     "$options": "i"}},
            {"doctor": {"$regex": f"^{doctor['username']}$", "$options": "i"}}
        ],
        "date":    today_date,
        "history": {"$ne": True}
    })

    if today_appointments == 0:
        flash("No appointments today!", "warning")
        return redirect(url_for("doctor_dashboard", username=username))

    session[token_key]      = session.get(token_key, 0) + 1
    session[token_time_key] = now.strftime("%Y-%m-%d %H:%M:%S")

    flash("Token advanced successfully!", "success")
    return redirect(url_for("doctor_dashboard", username=username))


# ================= DOCTOR DONE =================
@app.route("/doctor/done/<id>")
def doctor_done(id):
    appointments_col.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "Completed", "history": True}}
    )
    flash("Appointment marked as completed!", "success")
    return redirect(request.referrer)


# ================= DOCTOR CANCEL =================
@app.route("/doctor/cancel/<id>")
def doctor_cancel(id):
    appointments_col.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "Cancelled", "history": True}}
    )
    flash("Appointment cancelled!", "warning")
    return redirect(request.referrer)


# ================= STAFF DASHBOARD =================
@app.route("/staff")
def staff_dashboard():
    if session.get("role") != "staff":
        return redirect("/login")

    today_date = datetime.now().strftime("%Y-%m-%d")

    # All today's appointments with patient name lookup
    raw_appts = list(appointments_col.find({"date": today_date}).sort("token", 1))
    appointments = []
    for a in raw_appts:
        patient = patients_col.find_one({"username": a.get("username", "")}, {"name": 1})
        appointments.append({
            "id":           str(a["_id"]),
            "patient_name": patient["name"] if patient else a.get("username", "Unknown"),
            "username":     a.get("username", ""),
            "doctor":       a.get("doctor", ""),
            "time":         a.get("time", ""),
            "token":        a.get("token", 0),
            "status":       a.get("status", "Booked"),
            "source":       a.get("source", "online"),
            "history":      a.get("history", False),
        })

    # Doctor status list
    doctors_raw = list(doctors_col.find({}, {"name": 1, "department": 1,
                                              "leave_dates": 1, "break_start": 1,
                                              "break_end": 1, "status_override": 1}))
    doctors = []
    for d in doctors_raw:
        st = get_doctor_status(d["name"])
        count = appointments_col.count_documents({"doctor": d["name"], "date": today_date})
        doctors.append({
            "name":       d["name"],
            "department": d.get("department", ""),
            "status":     st["status"],
            "msg":        st["message"],
            "queue":      count,
        })

    # Ambulance / emergency requests
    emg_col     = appointments_col.database["ambulance_requests"]
    emergencies = list(emg_col.find(
        {"status": {"$in": ["pending", "dispatched"]}},
        sort=[("created_at", -1)]
    ))
    for e in emergencies:
        e["id"] = str(e["_id"])
        del e["_id"]

    # Prescriptions pending billing (no billing_status set, or explicitly pending)
    pending_billing = list(prescriptions_col.find(
        {"$or": [
            {"billing_status": {"$exists": False}},
            {"billing_status": None},
            {"billing_status": "pending_pricing"}
        ]},
        sort=[("created_at", -1)]
    ).limit(20))
    for p in pending_billing:
        p["id"] = str(p["_id"])
        del p["_id"]

    # Bills with payment screenshots awaiting verification
    bills_col = prescriptions_col.database["bills"]
    pending_payments = list(bills_col.find(
        {"status": "payment_submitted"},
        sort=[("payment_at", -1)]
    ))
    for b in pending_payments:
        b["id"] = str(b["_id"])
        del b["_id"]

    # Summary stats
    total_today     = len(appointments)
    completed_today = sum(1 for a in appointments if a["status"] == "Completed")
    waiting_today   = sum(1 for a in appointments if a["status"] in ("Booked", "Rescheduled"))
    available_docs  = sum(1 for d in doctors if d["status"] == "available")

    return render_template(
        "staff_dashboard.html",
        appointments=appointments,
        doctors=doctors,
        emergencies=emergencies,
        pending_billing=pending_billing,
        pending_payments=pending_payments,
        total_today=total_today,
        completed_today=completed_today,
        waiting_today=waiting_today,
        available_docs=available_docs,
        today_date=today_date,
        staff_username=session.get("username", "Staff"),
    )


# ================= STAFF: OFFLINE APPOINTMENT BOOKING =================
@app.route("/staff/book-appointment", methods=["POST"])
def staff_book_appointment():
    if session.get("role") != "staff":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    username = request.form.get("username", "").strip()
    doctor   = request.form.get("doctor",   "").strip()
    date     = request.form.get("date",     "").strip()
    time     = request.form.get("time",     "").strip()

    if not all([username, doctor, date, time]):
        flash("⚠️ All fields are required.", "error")
        return redirect("/staff")

    patient = patients_col.find_one({"username": username})
    if not patient:
        flash(f"❌ No patient found with username '{username}'. Please register them first.", "error")
        return redirect("/staff")

    hour, minute = map(int, time.split(":"))
    if hour < 9 or hour >= 21:
        flash("⏰ Appointments allowed only between 09:00 AM and 09:00 PM.", "error")
        return redirect("/staff")

    count    = appointments_col.count_documents({"doctor": doctor, "date": date})
    token    = count + 1
    avg_wait = f"{token * 8} mins"

    appointments_col.insert_one({
        "username":        username,
        "doctor":          doctor,
        "date":            date,
        "time":            time,
        "hospital":        "Ever Well Hospital",
        "token":           token,
        "avg_wait":        avg_wait,
        "status":          "Booked",
        "source":          "offline",
        "booked_by_staff": session.get("username", ""),
        "message":         "Appointment booked by staff",
        "created_at":      datetime.utcnow(),
        "history":         False,
    })

    flash(f"✅ Offline appointment booked for {patient.get('name', username)} with {doctor}.", "success")
    return redirect("/staff")


# ================= STAFF: LIVE APPOINTMENTS API =================
@app.route("/api/staff/appointments")
def api_staff_appointments():
    if session.get("role") != "staff":
        return jsonify({"error": "Unauthorized"}), 403

    today_date = datetime.now().strftime("%Y-%m-%d")
    raw_appts  = list(appointments_col.find({"date": today_date}).sort("token", 1))
    result = []
    for a in raw_appts:
        patient = patients_col.find_one({"username": a.get("username", "")}, {"name": 1})
        result.append({
            "id":           str(a["_id"]),
            "patient_name": patient["name"] if patient else a.get("username", "Unknown"),
            "username":     a.get("username", ""),
            "doctor":       a.get("doctor", ""),
            "time":         a.get("time", ""),
            "token":        a.get("token", 0),
            "status":       a.get("status", "Booked"),
            "source":       a.get("source", "online"),
            "history":      a.get("history", False),
        })
    return jsonify({"appointments": result, "total": len(result)})


# ================= STAFF: GENERATE BILL =================
@app.route("/staff/generate-bill", methods=["POST"])
def staff_generate_bill():
    if session.get("role") != "staff":
        return redirect("/login")

    prescription_id = request.form.get("prescription_id", "").strip()
    notes           = request.form.get("notes", "").strip()
    staff_username  = session.get("username", "")

    if not prescription_id:
        flash("❌ Prescription ID missing.", "error")
        return redirect("/staff")

    try:
        presc = prescriptions_col.find_one({"_id": ObjectId(prescription_id)})
    except Exception:
        flash("❌ Invalid prescription.", "error")
        return redirect("/staff")

    if not presc:
        flash("❌ Prescription not found.", "error")
        return redirect("/staff")

    # Parse medicines list from prescription
    meds_raw = presc.get("medicines", "")
    if isinstance(meds_raw, list):
        med_names = meds_raw
    else:
        lines = meds_raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        med_names = []
        for line in lines:
            for part in line.split(","):
                part = part.strip()
                if part:
                    med_names.append(part)

    # Build line items from form
    line_items  = []
    total_amount = 0.0
    for i, med_name in enumerate(med_names):
        qty   = float(request.form.get(f"med_qty_{i}",   1) or 1)
        price = float(request.form.get(f"med_price_{i}", 0) or 0)
        subtotal = qty * price
        total_amount += subtotal
        line_items.append({
            "medicine":   med_name,
            "quantity":   qty,
            "unit_price": price,
            "subtotal":   subtotal,
        })

    # Save bill to bills collection
    bills_col = prescriptions_col.database["bills"]
    bills_col.insert_one({
        "prescription_id":   ObjectId(prescription_id),
        "patient_username":  presc.get("patient_username", ""),
        "patient_name":      presc.get("patient_name", ""),
        "doctor":            presc.get("doctor", ""),
        "doctor_username":   presc.get("doctor_username", ""),
        "staff_username":    staff_username,
        "line_items":        line_items,
        "total_amount":      round(total_amount, 2),
        "notes":             notes,
        "status":            "sent",
        "created_at":        datetime.utcnow(),
    })

    # Mark prescription as billed
    prescriptions_col.update_one(
        {"_id": ObjectId(prescription_id)},
        {"$set": {"billing_status": "billed"}}
    )

    flash(
        f"✅ Bill of ₹{total_amount:,.2f} sent to {presc.get('patient_name', presc.get('patient_username', ''))}!",
        "success"
    )
    return redirect("/staff")


# ================= PATIENT: UPLOAD PAYMENT SCREENSHOT =================
import os, uuid
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/patient/pay-bill/<bill_id>", methods=["POST"])
def patient_pay_bill(bill_id):
    username = session.get("username")
    if not username:
        return redirect("/login")

    screenshot = request.files.get("screenshot")
    if not screenshot or screenshot.filename == "":
        flash("❌ Please select a payment screenshot to upload.", "error")
        return redirect(url_for("patient_dashboard", username=username))

    # Validate file type
    allowed = {"png", "jpg", "jpeg", "gif", "webp"}
    ext = screenshot.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        flash("❌ Only image files are allowed (PNG, JPG, GIF).", "error")
        return redirect(url_for("patient_dashboard", username=username))

    # Save file
    filename  = f"pay_{bill_id}_{uuid.uuid4().hex[:8]}.{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    screenshot.save(save_path)
    file_url  = f"/static/uploads/{filename}"

    bills_col = prescriptions_col.database["bills"]
    bills_col.update_one(
        {"_id": ObjectId(bill_id)},
        {"$set": {
            "status":             "payment_submitted",
            "payment_screenshot": file_url,
            "payment_at":         datetime.utcnow()
        }}
    )

    flash("✅ Payment screenshot uploaded! Staff will verify and confirm.", "success")
    return redirect(url_for("patient_dashboard", username=username))


# ================= STAFF: VERIFY PAYMENT =================
@app.route("/staff/verify-payment/<bill_id>", methods=["POST"])
def staff_verify_payment(bill_id):
    if session.get("role") != "staff":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    action = request.form.get("action", "approve")  # approve or reject
    bills_col = prescriptions_col.database["bills"]

    if action == "approve":
        bills_col.update_one(
            {"_id": ObjectId(bill_id)},
            {"$set": {"status": "paid", "verified_at": datetime.utcnow(),
                      "verified_by": session.get("username", "")}}
        )
        flash("✅ Payment verified and marked as Paid.", "success")
    else:
        bills_col.update_one(
            {"_id": ObjectId(bill_id)},
            {"$set": {"status": "sent", "payment_screenshot": "",
                      "rejection_note": request.form.get("note", "")}}
        )
        flash("❌ Payment rejected. Patient notified to re-upload.", "warning")

    return redirect("/staff")


# ================= ADMIN DASHBOARD =================
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect("/login")

    doctors = list(doctors_col.find())
    staff   = list(staff_col.find())

    # Doctor activity status
    for d in doctors:
        st = get_doctor_status(d["name"])
        d["status"]     = st["status"]
        d["status_msg"] = st["message"]
        d["_id"]        = str(d["_id"])

    for s in staff:
        s["_id"] = str(s["_id"])

    today_date       = datetime.now().strftime("%Y-%m-%d")
    all_appointments = list(appointments_col.find({"date": today_date}).sort("token", 1))
    for a in all_appointments:
        a["_id"] = str(a["_id"])

    # Total patients
    total_patients = patients_col.count_documents({})

    # Ambulance requests
    emg_col     = appointments_col.database["ambulance_requests"]
    emergencies = list(emg_col.find().sort("created_at", -1).limit(50))
    for e in emergencies:
        e["_id"] = str(e["_id"])

    # Verified bills (paid)
    bills_col     = prescriptions_col.database["bills"]
    verified_bills = list(bills_col.find({"status": "paid"}).sort("verified_at", -1).limit(30))
    for b in verified_bills:
        b["_id"] = str(b["_id"])

    # Overdue bills (sent > 24h ago, not paid)
    cutoff = datetime.utcnow() - timedelta(hours=24)
    overdue_bills = list(bills_col.find({
        "status":     {"$in": ["sent", "payment_submitted"]},
        "created_at": {"$lt": cutoff}
    }).sort("created_at", 1))
    for b in overdue_bills:
        b["_id"] = str(b["_id"])

    # All doctor ratings/reviews
    all_ratings = list(ratings_col.find().sort("submitted_at", -1).limit(50))
    for r in all_ratings:
        r["_id"] = str(r["_id"])
        if r.get("appointment_id"):
            r["appointment_id"] = str(r["appointment_id"])

    return render_template(
        "admin_dashboard.html",
        doctors=doctors,
        staff=staff,
        emergencies=emergencies,
        all_appointments=all_appointments,
        total_patients=total_patients,
        verified_bills=verified_bills,
        overdue_bills=overdue_bills,
        all_ratings=all_ratings,
        today_date=today_date,
    )


# ================= ADD DOCTOR =================
@app.route("/admin/add-doctor", methods=["POST"])
def admin_add_doctor():
    name       = request.form.get("name",       "").strip()
    department = request.form.get("department", "").strip()
    username   = request.form.get("username",   "").strip()
    password   = request.form.get("password",   "").strip()

    if not all([name, department, username, password]):
        flash("⚠️ All fields are required.", "error")
        return redirect("/admin")

    if doctors_col.find_one({"username": username}):
        flash(f"❌ Username '{username}' already exists. Choose a different one.", "error")
        return redirect("/admin")

    doctors_col.insert_one({
        "name":            name,
        "department":      department,
        "username":        username,
        "password":        password,
        "status_override": "available",
        "leave_dates":     [],
        "break_start":     "13:00",
        "break_end":       "14:00",
        "created_at":      datetime.utcnow(),
    })

    flash(f"✅ Dr. {name} ({department}) added successfully!", "success")
    return redirect("/admin")


# ================= ADD STAFF =================
@app.route("/admin/add-staff", methods=["POST"])
def admin_add_staff():
    name     = request.form.get("name",     "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    role     = request.form.get("role",     "").strip()

    if not all([name, username, password]):
        flash("⚠️ Name, username and password are required.", "error")
        return redirect("/admin")

    if staff_col.find_one({"username": username}):
        flash(f"❌ Username '{username}' already exists.", "error")
        return redirect("/admin")

    staff_col.insert_one({
        "name":       name,
        "username":   username,
        "password":   password,
        "role":       role,
        "created_at": datetime.utcnow(),
    })

    flash(f"✅ Staff member {name} added successfully!", "success")
    return redirect("/admin")


# ================= DELETE DOCTOR =================
@app.route("/admin/delete-doctor", methods=["POST"])
def admin_delete_doctor():
    doctor_id = request.form.get("doctor_id", "").strip()
    try:
        result = doctors_col.delete_one({"_id": ObjectId(doctor_id)})
        if result.deleted_count:
            flash("🗑️ Doctor removed successfully.", "success")
        else:
            flash("Doctor not found.", "error")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/admin")


# ================= DELETE STAFF =================
@app.route("/admin/delete-staff", methods=["POST"])
def admin_delete_staff():
    staff_id = request.form.get("staff_id", "").strip()
    try:
        result = staff_col.delete_one({"_id": ObjectId(staff_id)})
        if result.deleted_count:
            flash("🗑️ Staff member removed successfully.", "success")
        else:
            flash("Staff not found.", "error")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect("/admin")


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), use_reloader=True)