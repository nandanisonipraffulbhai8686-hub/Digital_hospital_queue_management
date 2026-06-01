# -*- coding: utf-8 -*-
"""
reminders.py
------------
Background scheduler that fires email + SMS reminders to patients
1 hour  before their appointment
5 minutes before their appointment

Setup required (fill in .env or set directly below):
  EMAIL_ADDRESS   – your Gmail address
  EMAIL_PASSWORD  – Gmail App Password (NOT your login password)
                    Generate at: https://myaccount.google.com/apppasswords
  TWILIO_SID      – Twilio Account SID
  TWILIO_TOKEN    – Twilio Auth Token
  TWILIO_FROM     – Twilio phone number  e.g. +1XXXXXXXXXX
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# ── optional: load a .env file if python-dotenv is installed ─────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Twilio (imported lazily so the app still starts if Twilio creds missing) ──
try:
    from twilio.rest import Client as TwilioClient
    _twilio_available = True
except ImportError:
    _twilio_available = False

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG  –  fill these in or set as environment variables
# ─────────────────────────────────────────────────────────────────────────────
EMAIL_ADDRESS  = os.environ.get("EMAIL_ADDRESS",  "your_gmail@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "your_app_password")   # Gmail App Password

TWILIO_SID   = os.environ.get("TWILIO_SID",   "")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN", "")
TWILIO_FROM  = os.environ.get("TWILIO_FROM",  "")   # e.g. +1XXXXXXXXXX


# ─────────────────────────────────────────────────────────────────────────────
# SEND EMAIL
# ─────────────────────────────────────────────────────────────────────────────
def send_email(to_address: str, subject: str, body: str):
    """Send a plain-text email via Gmail SMTP."""
    if not to_address or "@" not in to_address:
        log.warning("send_email: invalid address '%s', skipping.", to_address)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_ADDRESS
    msg["To"]      = to_address

    # Plain text part
    msg.attach(MIMEText(body, "plain"))

    # HTML part (nicer in Gmail)
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;padding:20px;">
      <div style="max-width:500px;margin:auto;border:1px solid #e0e0e0;border-radius:8px;padding:24px;">
        <h2 style="color:#1a73e8;">🏥 Hospital Appointment Reminder</h2>
        <p style="font-size:15px;">{body.replace(chr(10), '<br>')}</p>
        <hr style="border:none;border-top:1px solid #e0e0e0;margin:20px 0;">
        <p style="font-size:12px;color:#888;">Digital Hospital Queue System</p>
      </div>
    </body></html>
    """
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_address, msg.as_string())
        log.info("Email sent to %s | %s", to_address, subject)
    except Exception as e:
        log.error("Failed to send email to %s: %s", to_address, e)


# ─────────────────────────────────────────────────────────────────────────────
# SEND SMS
# ─────────────────────────────────────────────────────────────────────────────
def send_sms(to_number: str, body: str):
    """Send an SMS via Twilio."""
    if not _twilio_available:
        log.warning("Twilio not installed, skipping SMS.")
        return
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM]):
        log.warning("Twilio credentials not configured, skipping SMS.")
        return
    if not to_number:
        log.warning("send_sms: no phone number provided, skipping.")
        return

    # Normalise Indian mobile numbers → E.164
    number = to_number.strip().replace(" ", "").replace("-", "")
    if number.startswith("0"):
        number = "+91" + number[1:]
    elif not number.startswith("+"):
        number = "+91" + number   # assume India if no country code

    try:
        client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        message = client.messages.create(
            body=body,
            from_=TWILIO_FROM,
            to=number
        )
        log.info("SMS sent to %s | SID: %s", number, message.sid)
    except Exception as e:
        log.error("Failed to send SMS to %s: %s", number, e)


# ─────────────────────────────────────────────────────────────────────────────
# CORE REMINDER LOGIC
# ─────────────────────────────────────────────────────────────────────────────
def _check_and_send_reminders(appointments_col, patients_col):
    """
    Called every minute by the scheduler.
    Finds appointments whose time falls in the window:
      [now + target - 1min, now + target + 1min)
    for target = 60 min and 5 min.
    Uses a 'reminders_sent' set on each appointment doc to avoid duplicates.
    """
    now = datetime.now()

    for (label, minutes_ahead) in [("1hour", 60), ("5min", 5)]:
        target_dt  = now + timedelta(minutes=minutes_ahead)
        window_lo  = target_dt - timedelta(seconds=59)
        window_hi  = target_dt + timedelta(seconds=59)

        # Build date + time strings for the window
        # We query by date string and then filter by time in Python
        target_date = target_dt.strftime("%Y-%m-%d")

        candidates = list(appointments_col.find({
            "date":    target_date,
            "status":  {"$nin": ["Cancelled", "Completed"]},
            "history": {"$ne": True},
            f"reminders_sent.{label}": {"$ne": True}
        }))

        for appt in candidates:
            appt_time_str = appt.get("time", "")
            if not appt_time_str:
                continue

            try:
                appt_dt = datetime.strptime(
                    f"{target_date} {appt_time_str}", "%Y-%m-%d %H:%M"
                )
            except ValueError:
                continue

            # Check if this appointment falls in our ±1 min window
            if not (window_lo <= appt_dt <= window_hi):
                continue

            # ── Fetch patient contact details ──────────────────────────────
            patient = patients_col.find_one({"username": appt.get("username", "")})
            if not patient:
                continue

            patient_name = patient.get("name", appt.get("username", "Patient"))
            email        = patient.get("email",  "")
            mobile       = patient.get("mobile", "")
            doctor       = appt.get("doctor", "your doctor")
            appt_time    = appt_time_str
            token        = appt.get("token", "N/A")

            if minutes_ahead == 60:
                time_label = "1 hour"
            else:
                time_label = "5 minutes"

            subject = f"⏰ Appointment Reminder – {time_label} to go!"
            message = (
                f"Dear {patient_name},\n\n"
                f"This is a reminder that your appointment is in {time_label}.\n\n"
                f"  Doctor  : Dr. {doctor}\n"
                f"  Date    : {target_date}\n"
                f"  Time    : {appt_time}\n"
                f"  Token # : {token}\n\n"
                f"Please arrive a few minutes early and carry your token number.\n\n"
                f"Thank you,\nDigital Hospital Queue System"
            )

            # ── Send notifications ─────────────────────────────────────────
            if email:
                send_email(email, subject, message)
            if mobile:
                sms_body = (
                    f"Reminder: Your appointment with Dr. {doctor} is in {time_label}. "
                    f"Date: {target_date}, Time: {appt_time}, Token: {token}. "
                    f"- Digital Hospital"
                )
                send_sms(mobile, sms_body)

            # ── Mark as sent so we don't send again ────────────────────────
            appointments_col.update_one(
                {"_id": appt["_id"]},
                {"$set": {f"reminders_sent.{label}": True}}
            )
            log.info(
                "Reminder (%s) sent for appointment %s (patient: %s)",
                label, appt["_id"], appt.get("username")
            )


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULER SETUP
# ─────────────────────────────────────────────────────────────────────────────
_scheduler = None


def start_reminder_scheduler(appointments_col, patients_col):
    """
    Start the APScheduler background thread.
    Call this once from app.py at startup.
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        return  # already started (e.g. Flask debug reloader)

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        func=_check_and_send_reminders,
        trigger=IntervalTrigger(seconds=60),
        args=[appointments_col, patients_col],
        id="appointment_reminders",
        name="Appointment Reminder Job",
        replace_existing=True,
        misfire_grace_time=30
    )
    _scheduler.start()
    log.info("✅ Reminder scheduler started – checking every 60 seconds.")
