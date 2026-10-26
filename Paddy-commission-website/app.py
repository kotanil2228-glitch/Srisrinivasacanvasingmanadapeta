"""
SRI SRINIVASA CANVASING
Mandapeta, East Godavari District, Andhra Pradesh, India
Paddy Canvasing & Commission Business Web Application
"""

import os
import sys
import datetime
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort,
    send_from_directory,
)

import db
import auth

app = Flask(__name__)

# Application Configuration
app.secret_key = os.environ.get("SECRET_KEY", "srinivasa_secret_key_mandapeta_godavari_2026")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(hours=12)

# Ensure database tables exist & migrations run
db.migrate_and_init_db()


# ---------------- CONTEXT PROCESSORS & FILTERS ----------------

@app.context_processor
def inject_global_data():
    return {
        "business_name": "SRI SRINIVASA CANVASING",
        "business_location": "Mandapeta, East Godavari District, Andhra Pradesh",
        "business_address": "Main Road, Mandapeta, East Godavari District, AP - 533308",
        "current_year": datetime.datetime.now().year,
        "csrf_token": auth.generate_csrf_token,
        "mask_aadhaar": auth.mask_aadhaar,
        "mask_mobile": auth.mask_mobile,
    }


# ---------------- HOME ROUTE ----------------

@app.route("/")
def home():
    """
    Public Home Page:
    Accessible without logging in.
    Displays Sri Srinivasa Canvasing business introduction, Mandapeta East Godavari location,
    and action buttons for Farmer Login, Farmer Registration, and Admin Login.
    """
    return render_template("home.html")


# ---------------- FARMER REGISTRATION ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Farmer Registration:
    - Server-side validation of all fields (Name, Mobile, Aadhaar, Village, Password).
    - Validates 10-digit mobile number format and checks for duplicates.
    - Validates 12-digit Aadhaar number format.
    - Verifies password confirmation.
    - Hashes password securely before saving.
    """
    if request.method == "POST":
        token = request.form.get("csrf_token")
        if not auth.validate_csrf(token):
            flash("Security validation failed (CSRF). Please try again.", "danger")
            return redirect(url_for("register"))

        name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        aadhaar = request.form.get("aadhaar", "").strip()
        village = request.form.get("village", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Server-side validation
        errors = []
        if not name or len(name) < 2:
            errors.append("Please enter a valid farmer name.")
        if not auth.validate_mobile(mobile):
            errors.append("Please enter a valid 10-digit mobile number starting with 6, 7, 8, or 9.")
        if not auth.validate_aadhaar(aadhaar):
            errors.append("Please enter a valid 12-digit Aadhaar number.")
        if not village or len(village) < 2:
            errors.append("Please enter your village name.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        if password != confirm_password:
            errors.append("Password and Confirm Password do not match.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "register.html",
                name=name,
                mobile=mobile,
                aadhaar=aadhaar,
                village=village,
            )

        # Check duplicate mobile number
        existing = db.query_db("SELECT id FROM farmers WHERE mobile = ?", (mobile,), one=True)
        if existing:
            flash("Mobile number is already registered. Please login to your account.", "warning")
            return redirect(url_for("login"))

        # Secure password hashing
        pwd_hash = auth.hash_password(password)
        now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            db.query_db(
                """
                INSERT INTO farmers (name, mobile, aadhaar, village, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, mobile, aadhaar, village, pwd_hash, now_iso),
                commit=True,
            )
            flash("Registration successful! You can now log in with your mobile number.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"An error occurred while creating your account. Please try again.", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")


# ---------------- FARMER LOGIN & LOGOUT ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Farmer Login:
    - Verifies mobile number and hashed password.
    - Regenerates session to prevent fixation.
    - Redirects to farmer dashboard upon success.
    """
    if request.method == "POST":
        token = request.form.get("csrf_token")
        if not auth.validate_csrf(token):
            flash("Security check failed. Please refresh and try again.", "danger")
            return redirect(url_for("login"))

        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")

        if not mobile or not password:
            flash("Please enter both mobile number and password.", "danger")
            return render_template("login.html", mobile=mobile)

        farmer = db.query_db("SELECT * FROM farmers WHERE mobile = ?", (mobile,), one=True)

        if farmer:
            stored_hash = farmer["password_hash"]
            if stored_hash and auth.verify_password(password, stored_hash):
                session.clear()
                session.permanent = True
                session["user_id"] = farmer["id"]
                session["user_name"] = farmer["name"]
                session["mobile"] = farmer["mobile"]
                session["village"] = farmer["village"]
                session["role"] = "farmer"

                flash(f"Welcome back, {farmer['name']}!", "success")
                return redirect(url_for("farmer_dashboard"))
            elif not stored_hash and farmer.get("password") == password:
                new_hash = auth.hash_password(password)
                db.query_db("UPDATE farmers SET password_hash = ? WHERE id = ?", (new_hash, farmer["id"]), commit=True)
                session.clear()
                session.permanent = True
                session["user_id"] = farmer["id"]
                session["user_name"] = farmer["name"]
                session["mobile"] = farmer["mobile"]
                session["village"] = farmer["village"]
                session["role"] = "farmer"

                flash(f"Welcome, {farmer['name']}! Your account security was upgraded.", "success")
                return redirect(url_for("farmer_dashboard"))

        flash("Invalid mobile number or password. Please verify and try again.", "danger")
        return render_template("login.html", mobile=mobile)

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been safely logged out.", "info")
    return redirect(url_for("home"))


# ---------------- FARMER DASHBOARD ----------------

@app.route("/farmer/dashboard")
@auth.farmer_required
def farmer_dashboard():
    """
    Farmer Dashboard:
    - Displays farmer info.
    - Summary cards: Total, Pending, Approved, Rejected transactions.
    - Quick navigation to Submit Transaction, History, Receipts, Profile.
    - Recent transactions list with Status & Payment Status.
    """
    farmer_id = session.get("user_id")
    farmer = db.query_db("SELECT * FROM farmers WHERE id = ?", (farmer_id,), one=True)
    if not farmer:
        session.clear()
        return redirect(url_for("login"))

    total_tx = db.query_db("SELECT COUNT(*) FROM transactions WHERE farmer_id = ?", (farmer_id,), one=True)[0]
    pending_tx = db.query_db("SELECT COUNT(*) FROM transactions WHERE farmer_id = ? AND status = 'PENDING'", (farmer_id,), one=True)[0]
    approved_tx = db.query_db("SELECT COUNT(*) FROM transactions WHERE farmer_id = ? AND status = 'APPROVED'", (farmer_id,), one=True)[0]
    rejected_tx = db.query_db("SELECT COUNT(*) FROM transactions WHERE farmer_id = ? AND status = 'REJECTED'", (farmer_id,), one=True)[0]
    paid_tx = db.query_db("SELECT COUNT(*) FROM transactions WHERE farmer_id = ? AND payment_status = 'COMPLETED'", (farmer_id,), one=True)[0]

    recent_transactions = db.query_db(
        """
        SELECT t.*, r.mill_name AS current_mill_name
        FROM transactions t
        LEFT JOIN rice_mills r ON t.rice_mill_id = r.id
        WHERE t.farmer_id = ?
        ORDER BY t.id DESC
        LIMIT 5
        """,
        (farmer_id,),
    )

    return render_template(
        "farmer_dashboard.html",
        farmer=farmer,
        total_tx=total_tx,
        pending_tx=pending_tx,
        approved_tx=approved_tx,
        rejected_tx=rejected_tx,
        paid_tx=paid_tx,
        recent_transactions=recent_transactions,
    )


# ---------------- NEW PADDY TRANSACTION ----------------

@app.route("/farmer/transactions/new", methods=["GET", "POST"])
@auth.farmer_required
def new_transaction():
    farmer_id = session.get("user_id")
    farmer = db.query_db("SELECT * FROM farmers WHERE id = ?", (farmer_id,), one=True)
    if not farmer:
        return redirect(url_for("login"))

    active_mills = db.query_db(
        "SELECT id, mill_name, location FROM rice_mills WHERE is_active = 1 ORDER BY mill_name ASC"
    )

    if request.method == "POST":
        token = request.form.get("csrf_token")
        if not auth.validate_csrf(token):
            flash("Security check failed. Please submit again.", "danger")
            return redirect(url_for("new_transaction"))

        rice_mill_id = request.form.get("rice_mill_id")
        paddy_type = request.form.get("paddy_type", "").strip()
        number_of_bags = request.form.get("number_of_bags", "").strip()
        vehicle_number = request.form.get("vehicle_number", "").strip().upper()
        vehicle_weight_kg = request.form.get("vehicle_weight_kg", "").strip()
        driver_mobile = request.form.get("driver_mobile", "").strip()
        village = request.form.get("village", farmer["village"]).strip()

        errors = []

        if not active_mills:
            errors.append("No active rice mills are currently available. Please contact administrator.")
        elif not rice_mill_id:
            errors.append("Please select a rice mill from the list.")
        else:
            try:
                mill_record = db.query_db(
                    "SELECT id, mill_name, is_active FROM rice_mills WHERE id = ?",
                    (int(rice_mill_id),),
                    one=True,
                )
                if not mill_record:
                    errors.append("Selected rice mill does not exist.")
                elif not mill_record["is_active"]:
                    errors.append("Selected rice mill is currently inactive. Please choose an active mill.")
            except (ValueError, TypeError):
                errors.append("Invalid rice mill selection.")

        if not paddy_type:
            errors.append("Please select or enter the paddy variety/type.")

        try:
            bags_int = int(number_of_bags)
            if bags_int <= 0:
                errors.append("Number of bags must be greater than zero.")
        except ValueError:
            errors.append("Please enter a valid whole number for bags.")

        if not auth.validate_vehicle(vehicle_number):
            errors.append("Please enter a valid vehicle number (e.g., AP 31 TX 1234).")

        try:
            weight_val = float(vehicle_weight_kg)
            if weight_val <= 0:
                errors.append("Vehicle weight must be greater than zero kilograms.")
        except ValueError:
            errors.append("Please enter a valid numeric vehicle weight in kilograms.")

        if not auth.validate_mobile(driver_mobile):
            errors.append("Please enter a valid 10-digit driver mobile number.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "transaction_form.html",
                farmer=farmer,
                active_mills=active_mills,
                form_data=request.form,
            )

        transaction_id = auth.generate_transaction_id()
        mill_snapshot = mill_record["mill_name"]
        now_dt = datetime.datetime.now()
        timestamp_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

        try:
            db.query_db(
                """
                INSERT INTO transactions (
                    transaction_id, farmer_id, rice_mill_id, rice_mill_name_snapshot,
                    paddy_type, number_of_bags, vehicle_number, vehicle_weight_kg,
                    driver_mobile, transaction_timestamp, status, payment_status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 'PENDING', ?)
                """,
                (
                    transaction_id,
                    farmer_id,
                    int(rice_mill_id),
                    mill_snapshot,
                    paddy_type,
                    bags_int,
                    vehicle_number,
                    weight_val,
                    driver_mobile,
                    timestamp_str,
                    timestamp_str,
                ),
                commit=True,
            )

            flash(
                f"Paddy transaction {transaction_id} submitted successfully! Status: PENDING administrator approval.",
                "success",
            )
            return redirect(url_for("farmer_transactions"))

        except Exception as e:
            flash(f"Failed to submit transaction: {e}", "danger")
            return render_template(
                "transaction_form.html",
                farmer=farmer,
                active_mills=active_mills,
                form_data=request.form,
            )

    return render_template("transaction_form.html", farmer=farmer, active_mills=active_mills, form_data={})


# ---------------- FARMER TRANSACTION HISTORY & DETAILS ----------------

@app.route("/farmer/transactions")
@auth.farmer_required
def farmer_transactions():
    """
    Farmer Transaction History:
    - Search by Transaction ID.
    - Filter by Status (ALL, PENDING, APPROVED, REJECTED).
    - Filter by Payment Status (ALL, PENDING, COMPLETED).
    - Filter by Date.
    - Displays only transactions belonging to the logged-in farmer.
    - Shows Rice Mill name, Bags, Weight, Approval Status, and Payment Status.
    """
    farmer_id = session.get("user_id")
    search_q = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "ALL").strip().upper()
    payment_filter = request.args.get("payment_status", "ALL").strip().upper()
    date_filter = request.args.get("date", "").strip()

    sql = """
    SELECT t.*, r.mill_name AS current_mill_name
    FROM transactions t
    LEFT JOIN rice_mills r ON t.rice_mill_id = r.id
    WHERE t.farmer_id = ?
    """
    params = [farmer_id]

    if search_q:
        sql += " AND t.transaction_id LIKE ?"
        params.append(f"%{search_q}%")

    if status_filter in ["PENDING", "APPROVED", "REJECTED"]:
        sql += " AND t.status = ?"
        params.append(status_filter)

    if payment_filter in ["PENDING", "COMPLETED"]:
        sql += " AND t.payment_status = ?"
        params.append(payment_filter)

    if date_filter:
        sql += " AND t.transaction_timestamp LIKE ?"
        params.append(f"{date_filter}%")

    sql += " ORDER BY t.id DESC"

    transactions = db.query_db(sql, params)

    return render_template(
        "transaction_history.html",
        transactions=transactions,
        search_q=search_q,
        status_filter=status_filter,
        payment_filter=payment_filter,
        date_filter=date_filter,
    )


@app.route("/farmer/transactions/<tx_id>")
@auth.farmer_required
def farmer_transaction_details(tx_id):
    farmer_id = session.get("user_id")
    tx = db.query_db(
        """
        SELECT t.*, f.name AS farmer_name, f.mobile AS farmer_mobile, f.village AS farmer_village,
               r.mill_name AS current_mill_name, r.location AS mill_location
        FROM transactions t
        JOIN farmers f ON t.farmer_id = f.id
        LEFT JOIN rice_mills r ON t.rice_mill_id = r.id
        WHERE t.transaction_id = ? AND t.farmer_id = ?
        """,
        (tx_id, farmer_id),
        one=True,
    )

    if not tx:
        flash("Transaction not found or you do not have permission to view it.", "danger")
        return redirect(url_for("farmer_transactions"))

    return render_template("transaction_details.html", tx=tx)


# ---------------- ADMINISTRATOR LOGIN & LOGOUT ----------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        token = request.form.get("csrf_token")
        if not auth.validate_csrf(token):
            flash("Security check failed. Please refresh and try again.", "danger")
            return redirect(url_for("admin_login"))

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template("admin_login.html", username=username)

        admin = db.query_db("SELECT * FROM admins WHERE username = ?", (username,), one=True)

        if admin:
            stored_hash = admin["password_hash"]
            if stored_hash and auth.verify_password(password, stored_hash):
                session.clear()
                session.permanent = True
                session["user_id"] = admin["id"]
                session["username"] = admin["username"]
                session["role"] = "admin"

                flash(f"Administrator {admin['username']} authenticated successfully.", "success")
                return redirect(url_for("admin_dashboard"))
            elif not stored_hash and admin.get("password") == password:
                new_hash = auth.hash_password(password)
                db.query_db("UPDATE admins SET password_hash = ? WHERE id = ?", (new_hash, admin["id"]), commit=True)
                session.clear()
                session.permanent = True
                session["user_id"] = admin["id"]
                session["username"] = admin["username"]
                session["role"] = "admin"

                flash(f"Administrator {admin['username']} authenticated.", "success")
                return redirect(url_for("admin_dashboard"))

        flash("Invalid administrator credentials.", "danger")
        return render_template("admin_login.html", username=username)

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Administrator session closed.", "info")
    return redirect(url_for("admin_login"))


# ---------------- ADMINISTRATOR DASHBOARD ----------------

@app.route("/admin/dashboard")
@auth.admin_required
def admin_dashboard():
    total_farmers = db.query_db("SELECT COUNT(*) FROM farmers", one=True)[0]
    total_mills = db.query_db("SELECT COUNT(*) FROM rice_mills", one=True)[0]
    active_mills = db.query_db("SELECT COUNT(*) FROM rice_mills WHERE is_active = 1", one=True)[0]
    total_tx = db.query_db("SELECT COUNT(*) FROM transactions", one=True)[0]
    pending_tx = db.query_db("SELECT COUNT(*) FROM transactions WHERE status = 'PENDING'", one=True)[0]
    approved_tx = db.query_db("SELECT COUNT(*) FROM transactions WHERE status = 'APPROVED'", one=True)[0]
    rejected_tx = db.query_db("SELECT COUNT(*) FROM transactions WHERE status = 'REJECTED'", one=True)[0]
    paid_tx = db.query_db("SELECT COUNT(*) FROM transactions WHERE payment_status = 'COMPLETED'", one=True)[0]

    pending_transactions = db.query_db(
        """
        SELECT t.*, f.name AS farmer_name, f.mobile AS farmer_mobile, f.village AS farmer_village,
               r.mill_name AS current_mill_name
        FROM transactions t
        JOIN farmers f ON t.farmer_id = f.id
        LEFT JOIN rice_mills r ON t.rice_mill_id = r.id
        WHERE t.status = 'PENDING'
        ORDER BY t.id DESC
        LIMIT 10
        """
    )

    return render_template(
        "admin_dashboard.html",
        total_farmers=total_farmers,
        total_mills=total_mills,
        active_mills=active_mills,
        total_tx=total_tx,
        pending_tx=pending_tx,
        approved_tx=approved_tx,
        rejected_tx=rejected_tx,
        paid_tx=paid_tx,
        pending_transactions=pending_transactions,
    )


# ---------------- RICE MILL MANAGEMENT (ADMIN ONLY) ----------------

@app.route("/admin/rice-mills")
@auth.admin_required
def manage_rice_mills():
    search_q = request.args.get("q", "").strip()
    if search_q:
        mills = db.query_db(
            "SELECT * FROM rice_mills WHERE mill_name LIKE ? OR location LIKE ? ORDER BY id DESC",
            (f"%{search_q}%", f"%{search_q}%"),
        )
    else:
        mills = db.query_db("SELECT * FROM rice_mills ORDER BY id DESC")

    return render_template("manage_rice_mills.html", mills=mills, search_q=search_q)


@app.route("/admin/rice-mills/new", methods=["GET", "POST"])
@auth.admin_required
def add_rice_mill():
    if request.method == "POST":
        token = request.form.get("csrf_token")
        if not auth.validate_csrf(token):
            flash("Security check failed.", "danger")
            return redirect(url_for("add_rice_mill"))

        mill_name = request.form.get("mill_name", "").strip()
        location = request.form.get("location", "").strip()

        if not mill_name:
            flash("Rice mill name is required.", "danger")
            return render_template("rice_mill_form.html", mode="Add", mill_name=mill_name, location=location)

        existing = db.query_db(
            "SELECT id FROM rice_mills WHERE LOWER(TRIM(mill_name)) = LOWER(?)",
            (mill_name,),
            one=True,
        )
        if existing:
            flash(f"A rice mill with the name '{mill_name}' already exists.", "warning")
            return render_template("rice_mill_form.html", mode="Add", mill_name=mill_name, location=location)

        now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.query_db(
            "INSERT INTO rice_mills (mill_name, location, is_active, created_at, updated_at) VALUES (?, ?, 1, ?, ?)",
            (mill_name, location, now_iso, now_iso),
            commit=True,
        )
        flash(f"Rice mill '{mill_name}' added successfully.", "success")
        return redirect(url_for("manage_rice_mills"))

    return render_template("rice_mill_form.html", mode="Add", mill_name="", location="")


@app.route("/admin/rice-mills/<int:mill_id>/edit", methods=["GET", "POST"])
@auth.admin_required
def edit_rice_mill(mill_id):
    mill = db.query_db("SELECT * FROM rice_mills WHERE id = ?", (mill_id,), one=True)
    if not mill:
        flash("Rice mill not found.", "danger")
        return redirect(url_for("manage_rice_mills"))

    if request.method == "POST":
        token = request.form.get("csrf_token")
        if not auth.validate_csrf(token):
            flash("Security check failed.", "danger")
            return redirect(url_for("edit_rice_mill", mill_id=mill_id))

        mill_name = request.form.get("mill_name", "").strip()
        location = request.form.get("location", "").strip()

        if not mill_name:
            flash("Rice mill name cannot be empty.", "danger")
            return render_template("rice_mill_form.html", mode="Edit", mill=mill, mill_name=mill_name, location=location)

        existing = db.query_db(
            "SELECT id FROM rice_mills WHERE LOWER(TRIM(mill_name)) = LOWER(?) AND id != ?",
            (mill_name, mill_id),
            one=True,
        )
        if existing:
            flash(f"Another rice mill with the name '{mill_name}' already exists.", "warning")
            return render_template("rice_mill_form.html", mode="Edit", mill=mill, mill_name=mill_name, location=location)

        now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.query_db(
            "UPDATE rice_mills SET mill_name = ?, location = ?, updated_at = ? WHERE id = ?",
            (mill_name, location, now_iso, mill_id),
            commit=True,
        )
        flash(f"Rice mill '{mill_name}' updated successfully.", "success")
        return redirect(url_for("manage_rice_mills"))

    return render_template("rice_mill_form.html", mode="Edit", mill=mill, mill_name=mill["mill_name"], location=mill["location"])


@app.route("/admin/rice-mills/<int:mill_id>/toggle", methods=["POST"])
@auth.admin_required
def toggle_rice_mill(mill_id):
    token = request.form.get("csrf_token")
    if not auth.validate_csrf(token):
        flash("Security check failed.", "danger")
        return redirect(url_for("manage_rice_mills"))

    mill = db.query_db("SELECT id, mill_name, is_active FROM rice_mills WHERE id = ?", (mill_id,), one=True)
    if not mill:
        flash("Rice mill not found.", "danger")
        return redirect(url_for("manage_rice_mills"))

    new_status = 0 if mill["is_active"] else 1
    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.query_db(
        "UPDATE rice_mills SET is_active = ?, updated_at = ? WHERE id = ?",
        (new_status, now_iso, mill_id),
        commit=True,
    )

    action_label = "activated" if new_status == 1 else "deactivated"
    flash(f"Rice mill '{mill['mill_name']}' has been {action_label}.", "info")
    return redirect(url_for("manage_rice_mills"))


# ---------------- ADMIN TRANSACTION MANAGEMENT & APPROVAL ----------------

@app.route("/admin/transactions")
@auth.admin_required
def admin_transactions():
    search_q = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "ALL").strip().upper()
    payment_filter = request.args.get("payment_status", "ALL").strip().upper()
    mill_filter = request.args.get("mill_id", "").strip()
    date_filter = request.args.get("date", "").strip()

    sql = """
    SELECT t.*, f.name AS farmer_name, f.mobile AS farmer_mobile, f.village AS farmer_village,
           r.mill_name AS current_mill_name
    FROM transactions t
    JOIN farmers f ON t.farmer_id = f.id
    LEFT JOIN rice_mills r ON t.rice_mill_id = r.id
    WHERE 1=1
    """
    params = []

    if search_q:
        sql += """ AND (
            t.transaction_id LIKE ? OR
            f.name LIKE ? OR
            f.mobile LIKE ? OR
            t.vehicle_number LIKE ? OR
            t.rice_mill_name_snapshot LIKE ? OR
            r.mill_name LIKE ?
        )"""
        q_wild = f"%{search_q}%"
        params.extend([q_wild, q_wild, q_wild, q_wild, q_wild, q_wild])

    if status_filter in ["PENDING", "APPROVED", "REJECTED"]:
        sql += " AND t.status = ?"
        params.append(status_filter)

    if payment_filter in ["PENDING", "COMPLETED"]:
        sql += " AND t.payment_status = ?"
        params.append(payment_filter)

    if mill_filter:
        try:
            sql += " AND t.rice_mill_id = ?"
            params.append(int(mill_filter))
        except ValueError:
            pass

    if date_filter:
        sql += " AND t.transaction_timestamp LIKE ?"
        params.append(f"{date_filter}%")

    sql += " ORDER BY t.id DESC"

    transactions = db.query_db(sql, params)
    mills = db.query_db("SELECT id, mill_name FROM rice_mills ORDER BY mill_name ASC")

    return render_template(
        "admin_transactions.html",
        transactions=transactions,
        mills=mills,
        search_q=search_q,
        status_filter=status_filter,
        payment_filter=payment_filter,
        mill_filter=mill_filter,
        date_filter=date_filter,
    )


@app.route("/admin/transactions/<tx_id>")
@auth.admin_required
def admin_transaction_details(tx_id):
    tx = db.query_db(
        """
        SELECT t.*, f.name AS farmer_name, f.mobile AS farmer_mobile, f.village AS farmer_village,
               f.aadhaar AS farmer_aadhaar,
               r.mill_name AS current_mill_name, r.location AS mill_location,
               a.username AS decider_admin_username
        FROM transactions t
        JOIN farmers f ON t.farmer_id = f.id
        LEFT JOIN rice_mills r ON t.rice_mill_id = r.id
        LEFT JOIN admins a ON t.decided_by_admin_id = a.id
        WHERE t.transaction_id = ?
        """,
        (tx_id,),
        one=True,
    )

    if not tx:
        flash("Transaction not found.", "danger")
        return redirect(url_for("admin_transactions"))

    mills = db.query_db("SELECT id, mill_name FROM rice_mills WHERE is_active = 1 ORDER BY mill_name ASC")

    return render_template("admin_transaction_details.html", tx=tx, mills=mills)


@app.route("/admin/transactions/<tx_id>/decision", methods=["POST"])
@auth.admin_required
def admin_transaction_decision(tx_id):
    token = request.form.get("csrf_token")
    if not auth.validate_csrf(token):
        flash("Security validation failed.", "danger")
        return redirect(url_for("admin_transaction_details", tx_id=tx_id))

    decision = request.form.get("decision", "").strip().upper()
    rejection_reason = request.form.get("rejection_reason", "").strip()

    if decision not in ["APPROVED", "REJECTED"]:
        flash("Invalid decision specified.", "danger")
        return redirect(url_for("admin_transaction_details", tx_id=tx_id))

    tx = db.query_db("SELECT id, status, transaction_id FROM transactions WHERE transaction_id = ?", (tx_id,), one=True)
    if not tx:
        flash("Transaction not found.", "danger")
        return redirect(url_for("admin_transactions"))

    if tx["status"] != "PENDING":
        flash(
            f"Transaction {tx_id} has already been processed with status '{tx['status']}'. Repeated decisions are prevented.",
            "warning",
        )
        return redirect(url_for("admin_transaction_details", tx_id=tx_id))

    admin_id = session.get("user_id")
    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.query_db(
        """
        UPDATE transactions
        SET status = ?, decided_by_admin_id = ?, decision_timestamp = ?, rejection_reason = ?
        WHERE transaction_id = ? AND status = 'PENDING'
        """,
        (decision, admin_id, now_iso, rejection_reason if decision == "REJECTED" else None, tx_id),
        commit=True,
    )

    if decision == "APPROVED":
        verify_url = request.url_root.rstrip("/") + url_for("verify_transaction", tx_id=tx_id)
        qr_dir = os.path.join(app.root_path, "static", "qr")
        auth.save_qr_file(verify_url, tx_id, qr_dir)

    flash(f"Transaction {tx_id} successfully marked as {decision}.", "success")
    return redirect(url_for("admin_transaction_details", tx_id=tx_id))


# ---------------- ADMIN PAYMENT COMPLETION WORKFLOW ----------------

@app.route("/admin/transactions/<tx_id>/payment", methods=["POST"])
@auth.admin_required
def admin_transaction_payment(tx_id):
    """
    Admin feature: Mark payment as completed or pending for a transaction.
    This settlement status is immediately visible to the farmer across their
    dashboard, transaction history, details, and receipt.
    """
    token = request.form.get("csrf_token")
    if not auth.validate_csrf(token):
        flash("Security validation failed.", "danger")
        return redirect(url_for("admin_transaction_details", tx_id=tx_id))

    tx = db.query_db("SELECT id, status, payment_status FROM transactions WHERE transaction_id = ?", (tx_id,), one=True)
    if not tx:
        flash("Transaction not found.", "danger")
        return redirect(url_for("admin_transactions"))

    payment_status = request.form.get("payment_status", "COMPLETED").strip().upper()
    payment_notes = request.form.get("payment_notes", "").strip()
    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if payment_status == "COMPLETED":
        db.query_db(
            """
            UPDATE transactions
            SET payment_status = 'COMPLETED', payment_timestamp = ?, payment_notes = ?
            WHERE transaction_id = ?
            """,
            (now_iso, payment_notes or "Settled via Sri Srinivasa Canvasing office", tx_id),
            commit=True,
        )
        flash(f"Payment marked as COMPLETED for transaction {tx_id}. The farmer can now see this status.", "success")
    else:
        db.query_db(
            """
            UPDATE transactions
            SET payment_status = 'PENDING', payment_timestamp = NULL, payment_notes = ?
            WHERE transaction_id = ?
            """,
            (payment_notes, tx_id),
            commit=True,
        )
        flash(f"Payment status reset to PENDING for transaction {tx_id}.", "info")

    return redirect(url_for("admin_transaction_details", tx_id=tx_id))


@app.route("/admin/transactions/<tx_id>/assign-mill", methods=["POST"])
@auth.admin_required
def admin_assign_mill(tx_id):
    token = request.form.get("csrf_token")
    if not auth.validate_csrf(token):
        flash("Security validation failed.", "danger")
        return redirect(url_for("admin_transaction_details", tx_id=tx_id))

    mill_id = request.form.get("rice_mill_id")
    if not mill_id:
        flash("Please select a rice mill.", "warning")
        return redirect(url_for("admin_transaction_details", tx_id=tx_id))

    mill = db.query_db("SELECT id, mill_name FROM rice_mills WHERE id = ?", (int(mill_id),), one=True)
    if not mill:
        flash("Selected rice mill does not exist.", "danger")
        return redirect(url_for("admin_transaction_details", tx_id=tx_id))

    db.query_db(
        "UPDATE transactions SET rice_mill_id = ?, rice_mill_name_snapshot = ? WHERE transaction_id = ?",
        (mill["id"], mill["mill_name"], tx_id),
        commit=True,
    )

    flash(f"Rice mill '{mill['mill_name']}' assigned to transaction {tx_id}.", "success")
    return redirect(url_for("admin_transaction_details", tx_id=tx_id))


# ---------------- ADMIN FARMERS DIRECTORY ----------------

@app.route("/admin/farmers")
@auth.admin_required
def admin_farmers():
    farmers = db.query_db(
        """
        SELECT f.*, COUNT(t.id) AS tx_count
        FROM farmers f
        LEFT JOIN transactions t ON f.id = t.farmer_id
        GROUP BY f.id
        ORDER BY f.id DESC
        """
    )
    return render_template("admin_farmers.html", farmers=farmers)


# ---------------- RECEIPT GENERATION & PRINTING ----------------

@app.route("/receipt/<tx_id>")
def view_receipt(tx_id):
    role = session.get("role")
    user_id = session.get("user_id")

    if not user_id:
        flash("Please log in to view this receipt.", "warning")
        return redirect(url_for("login"))

    tx = db.query_db(
        """
        SELECT t.*, f.name AS farmer_name, f.mobile AS farmer_mobile, f.village AS farmer_village,
               r.mill_name AS current_mill_name, r.location AS mill_location,
               a.username AS decider_admin_username
        FROM transactions t
        JOIN farmers f ON t.farmer_id = f.id
        LEFT JOIN rice_mills r ON t.rice_mill_id = r.id
        LEFT JOIN admins a ON t.decided_by_admin_id = a.id
        WHERE t.transaction_id = ?
        """,
        (tx_id,),
        one=True,
    )

    if not tx:
        abort(404)

    if role == "farmer" and tx["farmer_id"] != user_id:
        abort(403)

    if tx["status"] != "APPROVED":
        flash("Receipts are generated only for APPROVED transactions.", "warning")
        if role == "admin":
            return redirect(url_for("admin_transaction_details", tx_id=tx_id))
        return redirect(url_for("farmer_transaction_details", tx_id=tx_id))

    verify_url = request.url_root.rstrip("/") + url_for("verify_transaction", tx_id=tx_id)
    qr_data_uri = auth.generate_qr_data_uri(verify_url)

    qr_dir = os.path.join(app.root_path, "static", "qr")
    auth.save_qr_file(verify_url, tx_id, qr_dir)

    return render_template(
        "receipt.html",
        tx=tx,
        verify_url=verify_url,
        qr_data_uri=qr_data_uri,
    )


# ---------------- QR CODE PUBLIC VERIFICATION ----------------

@app.route("/verify/<tx_id>")
def verify_transaction(tx_id):
    tx = db.query_db(
        """
        SELECT t.transaction_id, t.paddy_type, t.number_of_bags, t.vehicle_number,
               t.vehicle_weight_kg, t.transaction_timestamp, t.status, t.decision_timestamp,
               t.rice_mill_name_snapshot, t.payment_status, t.payment_timestamp, t.payment_notes,
               r.mill_name AS current_mill_name, r.location AS mill_location,
               f.name AS farmer_name, f.village AS farmer_village
        FROM transactions t
        JOIN farmers f ON t.farmer_id = f.id
        LEFT JOIN rice_mills r ON t.rice_mill_id = r.id
        WHERE t.transaction_id = ?
        """,
        (tx_id,),
        one=True,
    )

    return render_template("verify_transaction.html", tx=tx, query_id=tx_id)


# ---------------- ERROR HANDLERS ----------------

@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="Access Forbidden: You do not have permission to view this resource."), 403


@app.errorhandler(404)
def page_not_found(e):
    return render_template("error.html", code=404, message="Page or record not found."), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="An internal server error occurred. Please contact system support."), 500


# ---------------- CLI AND STARTUP ----------------

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--create-admin":
        if len(sys.argv) >= 4:
            new_u = sys.argv[2]
            new_p = sys.argv[3]
            h = auth.hash_password(new_p)
            now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.query_db(
                "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
                (new_u, h, now_iso),
                commit=True,
            )
            print(f"Admin '{new_u}' created successfully.")
        else:
            print("Usage: python app.py --create-admin <username> <password>")
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "--init-db":
        db.migrate_and_init_db()
        print("Database schema successfully migrated & initialized.")
        sys.exit(0)

    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
