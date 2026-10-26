"""
SRI SRINIVASA CANVASING - Authentication, Security, Validation & Utilities
Mandapeta, Andhra Pradesh
"""

import os
import re
import io
import base64
import secrets
import string
import datetime
from functools import wraps
from flask import session, redirect, url_for, flash, request, abort, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
from PIL import Image

import db


def hash_password(password: str) -> str:
    """Hash password securely using Werkzeug's default scrypt / pbkdf2."""
    return generate_password_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Safely verify hashed password."""
    if not hashed_password:
        return False
    return check_password_hash(hashed_password, plain_password)


def mask_aadhaar(aadhaar: str) -> str:
    """
    Masks 12-digit Aadhaar to display only the last 4 digits:
    e.g. 123456789012 -> XXXX-XXXX-9012
    """
    if not aadhaar:
        return ""
    clean = re.sub(r"\D", "", str(aadhaar))
    if len(clean) >= 4:
        last4 = clean[-4:]
        return f"XXXX-XXXX-{last4}"
    return "XXXX-XXXX-XXXX"


def mask_mobile(mobile: str) -> str:
    """
    Masks 10-digit mobile number:
    e.g. 9848012345 -> 98480****5
    """
    if not mobile:
        return ""
    clean = re.sub(r"\D", "", str(mobile))
    if len(clean) == 10:
        return f"{clean[:5]}****{clean[-1]}"
    elif len(clean) > 4:
        return f"{clean[:2]}****{clean[-2:]}"
    return clean


def validate_mobile(mobile: str) -> bool:
    """Validates 10-digit Indian mobile number starting with 6, 7, 8, or 9."""
    if not mobile:
        return False
    return bool(re.match(r"^[6-9]\d{9}$", str(mobile).strip()))


def validate_aadhaar(aadhaar: str) -> bool:
    """Validates 12-digit Aadhaar number."""
    if not aadhaar:
        return False
    clean = re.sub(r"[\s\-]", "", str(aadhaar).strip())
    return bool(re.match(r"^\d{12}$", clean))


def validate_vehicle(vehicle: str) -> bool:
    """Checks that vehicle number is non-empty and reasonably structured."""
    if not vehicle:
        return False
    v = vehicle.strip().upper()
    return len(v) >= 4 and len(v) <= 20


def generate_csrf_token() -> str:
    """Generates and persists CSRF token in session."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(24)
    return session["_csrf_token"]


def validate_csrf(token: str) -> bool:
    """Verifies CSRF token from form submission."""
    try:
        if current_app and current_app.config.get("TESTING"):
            return True
    except Exception:
        pass

    session_token = session.get("_csrf_token")
    if not session_token or not token:
        return False
    return secrets.compare_digest(session_token, token)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def farmer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id") or session.get("role") != "farmer":
            flash("Farmer authentication required.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id") or session.get("role") != "admin":
            flash("Administrator authentication required.", "danger")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function


def generate_transaction_id() -> str:
    """
    Generates a unique, readable transaction ID in the format:
    SSC-YYYYMMDD-XXXXXXXX
    Ensures uniqueness via database verification.
    """
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    chars = string.ascii_uppercase + string.digits

    max_attempts = 10
    for _ in range(max_attempts):
        suffix = "".join(secrets.choice(chars) for _ in range(8))
        tx_id = f"SSC-{today_str}-{suffix}"

        # Collision check against database
        existing = db.query_db("SELECT id FROM transactions WHERE transaction_id = ?", (tx_id,), one=True)
        if not existing:
            return tx_id

    # Fallback with timestamp microsecond suffix if extreme collision occurs
    micro = datetime.datetime.now().strftime("%f")[:4]
    suffix = "".join(secrets.choice(chars) for _ in range(4)) + micro
    return f"SSC-{today_str}-{suffix}"


def generate_qr_data_uri(verify_url: str) -> str:
    """
    Generates a QR Code for the verification URL and returns a base64 data URI (image/png).
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0B1B3D", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


def save_qr_file(verify_url: str, transaction_id: str, output_dir: str) -> str:
    """
    Saves QR code image to static/qr/<transaction_id>.png and returns relative URL.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{transaction_id}.png"
    file_path = os.path.join(output_dir, filename)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0B1B3D", back_color="white")
    img.save(file_path, format="PNG")
    return f"/static/qr/{filename}"
