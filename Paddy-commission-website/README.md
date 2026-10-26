# SRI SRINIVASA CANVASING — PADDY COMMISSION PLATFORM
**Mandapeta, East Godavari District, Andhra Pradesh, India**

A secure, professional, responsive, and full-featured web application built for **SRI SRINIVASA CANVASING**, a premier family-owned paddy canvasing and commission agency located in Mandapeta, Andhra Pradesh.

---

## 🌾 Business Profile & Context

* **Business Name:** SRI SRINIVASA CANVASING
* **Head Office:** Main Road, Mandapeta, East Godavari District, Andhra Pradesh - 533308
* **Operational Scope:** Bridging paddy farmers across the Godavari delta with modern rice mills. Providing transparent vehicle dispatch recording, bag counts, weighbridge reconciliation, administrative approval, and instant official receipts with cryptographic QR code verification.

---

## 🚀 Key Features

### 1. Farmer Portal
* **Farmer Registration & Login:** Validates 10-digit Indian mobile numbers (`^[6-9]\d{9}$`), 12-digit Aadhaar, village origin, and enforces strong hashed passwords (`scrypt` / `pbkdf2`).
* **Aadhaar Privacy Protection:** Sensitive Aadhaar numbers are never stored in plaintext and are masked in all user-facing interfaces (e.g. `XXXX-XXXX-1234`).
* **Farmer Dashboard:** Summary cards for Total, Pending, Approved, and Rejected transactions with quick navigation.
* **New Paddy Booking:** Auto-generates unique Transaction IDs (`SSC-YYYYMMDD-XXXXXXXX`), pre-fills authenticated farmer details, and provides a **database-backed dropdown of active authorized rice mills**.
* **Transaction History & Tracking:** Live filtering by status (`PENDING`, `APPROVED`, `REJECTED`), date, and Transaction ID search.

### 2. Rice Mill Management (Administrator Feature)
* **Dedicated Database Table (`rice_mills`):** Stores Mill Name, Location, Status (`is_active`), and Timestamps.
* **Full CRUD & Search:** Add new partner mills, edit details, and search by name or location.
* **Active / Inactive Toggle:** Deactivated mills are immediately removed from farmer booking forms, while **historical transactions linked to deactivated mills remain 100% preserved**.
* **Duplicate Prevention:** Case-insensitive normalization checks prevent unintended duplicates.

### 3. Paddy Transaction Lifecycle & Administrative Audit
* **Unique Transaction ID Format:** `SSC-YYYYMMDD-XXXXXXXX` (e.g., `SSC-20261026-F98B23E1`) enforced with database uniqueness constraints.
* **Status Workflow:** `PENDING` &rarr; `APPROVED` or `REJECTED`.
* **Double-Decision & Race Condition Prevention:** Transactions can only be decided once from a `PENDING` state; concurrent or repeated decisions are safely rejected.
* **Audit Metadata:** Records deciding administrator ID, decision timestamp, and optional rejection reason.
* **Historical Data Compatibility:** Supports legacy transactions where `rice_mill_id` is null, displaying `"Not recorded"` and offering an admin mill-assignment workflow without resetting the database.

### 4. Official Receipts, Printing & QR Code Verification
* **A4 Print-Optimized Layout (`print.css`):** Formatted for standard desktop/office printers, hiding navigation and dashboard controls while featuring a subtle Lord Balaji watermark.
* **Live QR Code Generation:** Each approved receipt embeds a scannable QR code generated using `qrcode` and `Pillow`.
* **Public QR Verification Page (`/verify/<tx_id>`):** Scanned receipts retrieve live database records to display verification status, mill name, bags, and date, without exposing sensitive personal information.

---

## 🛠️ Technology Stack

* **Backend:** Python 3.11+, Flask 3.1+
* **Security:** Werkzeug password hashing, Flask session management, CSRF token verification
* **Databases:**
  * **Local Development:** SQLite (`database.db`) with foreign key enforcement
  * **Production:** PostgreSQL via `DATABASE_URL` connection string
* **Frontend:** HTML5, CSS3 (Custom Gold, Dark Blue, and White palette), Responsive JavaScript
* **Imaging & QR:** `qrcode[pil]`, `Pillow`
* **Styling Assets:** Traditional auspicious theme with Lord Balaji watermark and glassmorphic translucent cards

---

## 📁 Project Directory Structure

```text
Paddy-commission-website/
├── app.py                     # Main Flask application with routes, error handlers, and CLI
├── db.py                      # Database abstraction layer (SQLite & PostgreSQL migrations)
├── auth.py                    # Security utilities, validation, hashing, decorators, QR generation
├── migrate_to_postgres.py     # Data migration script from SQLite to PostgreSQL
├── requirements.txt           # Project dependencies
├── .env.example               # Template environment configuration
├── .gitignore                 # Git ignore rules
├── README.md                  # System documentation
├── database.db                # Local development SQLite database (auto-generated)
│
├── static/
│   ├── balaji.jpg             # Lord Venkateswara background image
│   ├── images/
│   │   └── balaji.jpg         # Asset fallback copy
│   ├── css/
│   │   ├── style.css          # Gold, Dark Blue & Cream traditional responsive styling
│   │   └── print.css          # A4 print-optimized receipt layout
│   ├── js/
│   │   └── main.js            # Mobile navbar, alerts, weight estimator, print trigger
│   └── qr/                    # Generated QR verification images
│
├── templates/
│   ├── base.html              # Core layout with branding, navbar, alerts, footer
│   ├── home.html              # Public landing page with business overview
│   ├── login.html             # Farmer login
│   ├── register.html          # Farmer registration with Aadhaar protection
│   ├── farmer_dashboard.html  # Farmer dashboard with summary cards & action hub
│   ├── transaction_form.html  # New Paddy Transaction with dynamic rice mill dropdown
│   ├── transaction_history.html # Farmer transaction ledger with filters
│   ├── transaction_details.html # Detailed view of farmer transaction
│   ├── admin_login.html       # Administrator portal login
│   ├── admin_dashboard.html   # Admin console with system metrics & approval queue
│   ├── manage_rice_mills.html # Rice mill management table & search
│   ├── rice_mill_form.html    # Add / Edit rice mill form
│   ├── admin_transactions.html# Admin searchable transaction ledger
│   ├── admin_transaction_details.html # Admin decision modal with rejection reason
│   ├── admin_farmers.html     # Registered farmers directory
│   ├── receipt.html           # Official printable Paddy Memo / Receipt with QR
│   ├── verify_transaction.html# Public QR code scan verification page
│   └── error.html             # Custom 403, 404, 500 error display
│
└── tests/
    └── test_app.py            # Automated test suite (all 37 requirements)
```

---

## 💻 Local Development Setup in VS Code

### Step 1: Clone or Open in VS Code
Open the project directory in VS Code:
```bash
cd "c:\Users\kotaa\OneDrive\Desktop\VS CODE\Paddy-commission-website"
code .
```

### Step 2: Create and Activate a Virtual Environment
```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Default development settings will use local SQLite (`database.db`) automatically.

### Step 5: Initialize Database & Administrator
```bash
# Initialize schema and seed default Mandapeta rice mills
python app.py --init-db

# (Optional) Create a custom administrator account:
python app.py --create-admin admin Admin@123
```
*Default Administrator Credentials:*
* **Username:** `admin`
* **Password:** `Admin@123`

### Step 6: Start the Development Server
```bash
python app.py
```
Open your browser to: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 Automated Testing

The project includes an automated test suite verifying all 37 functional, security, and integrity requirements.

To run the full test suite:
```bash
python tests/test_app.py
```

### Test Coverage Summary:
* **Farmers (Tests 1–7):** Registration, duplicate mobile prevention, mobile regex validation, password hashing, valid/invalid logins, session clearing on logout.
* **Rice Mills (Tests 8–15):** Adding mills, editing mills, active/inactive toggles, duplicate name handling, dropdown filtering, backend rejection of inactive/invalid mill IDs, farmer permission restrictions.
* **Transactions (Tests 16–27):** Valid submission, `PENDING` initial status, `SSC-YYYYMMDD-XXXXXXXX` unique format, history & details linkage, admin approval & rejection, rejection reasons, repeated decision prevention, farmer ownership boundaries, admin search & filtering.
* **Receipts & QR (Tests 28–33):** Approved transaction receipts, rice mill name snapshot accuracy, historical receipt support without mill, live QR verification, privacy protection (no Aadhaar/password exposure), print CSS button hiding.
* **Database (Tests 34–37):** Non-destructive migrations, transaction persistence across re-connections, foreign key constraints, safe error handling and rollbacks.

**Result: 37 / 37 Tests Passed (100% Passing).**

---

## 🐘 PostgreSQL Production Deployment

### 1. Database Connection String
To switch from SQLite to PostgreSQL in production, set the `DATABASE_URL` environment variable:
```bash
DATABASE_URL=postgresql://srinivasa_user:your_password@db-host:5432/srinivasa_db
```
The database adapter in `db.py` automatically detects PostgreSQL, configures `psycopg2`, and initializes the PostgreSQL schema.

### 2. Migrating Existing SQLite Records to PostgreSQL
To copy all farmers, admins, rice mills, and transactions from local SQLite to PostgreSQL without loss:
```bash
# Set your production database URL
set DATABASE_URL=postgresql://user:password@host:5432/dbname

# Execute migration script
python migrate_to_postgres.py
```

### 3. Production Deployment Recommendations
* **Hosting Platform:** Render, Railway, AWS EC2 / App Runner, or DigitalOcean App Platform.
* **Persistent Storage:** Attach a managed PostgreSQL database (e.g., Render Managed PostgreSQL or AWS RDS). Do not rely on ephemeral containers for data storage.
* **WSGI Production Server:** Run with `gunicorn` in Linux production environments:
  ```bash
  pip install gunicorn
  gunicorn -w 4 -b 0.0.0.0:5000 "app:app"
  ```
* **HTTPS:** Enforce SSL/TLS certificates (Let's Encrypt / Cloudflare) to safeguard login sessions and Aadhaar data.

---

## 📞 Business Contact

**SRI SRINIVASA CANVASING**  
Main Road, Mandapeta, East Godavari District, Andhra Pradesh - 533308.  
*Operating with devotion, trust, and transparency.*
