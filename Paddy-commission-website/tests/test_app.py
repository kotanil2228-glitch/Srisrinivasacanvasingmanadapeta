"""
SRI SRINIVASA CANVASING - Automated Test Suite
Mandapeta, Andhra Pradesh
Tests all 37 functional and security requirements.
"""

import os
import sys
import tempfile
import unittest
import sqlite3
import datetime

# Ensure project root is in sys.path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import db
import auth
from app import app


class SriSrinivasaCanvasingTestCase(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary SQLite database for each test run
        self.db_fd, self.db_path = tempfile.mkstemp(suffix="_test_srinivasa.db")
        os.environ["SQLITE_PATH"] = self.db_path
        os.environ["DATABASE_URL"] = ""

        # Configure Flask test client
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

        # Initialize schema and seed default admin & mills in test DB
        db.migrate_and_init_db()

    def tearDown(self):
        try:
            os.close(self.db_fd)
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except Exception:
            pass

    # Helper to get CSRF token in testing
    def get_csrf_token(self, path="/login"):
        return "test_csrf_token_val"

    # Helper to login as farmer
    def login_farmer(self, mobile="9848011111", password="FarmerPassword123"):
        csrf = self.get_csrf_token("/login")
        return self.client.post("/login", data={
            "csrf_token": csrf,
            "mobile": mobile,
            "password": password
        }, follow_redirects=True)

    # Helper to login as admin
    def login_admin(self, username="admin", password="Admin@123"):
        csrf = self.get_csrf_token("/admin/login")
        return self.client.post("/admin/login", data={
            "csrf_token": csrf,
            "username": username,
            "password": password
        }, follow_redirects=True)

    # Helper to register a test farmer
    def register_farmer(self, name="Varma", mobile="9848011111", aadhaar="123456789012",
                        village="Mandapeta", password="FarmerPassword123", confirm_password=None):
        if confirm_password is None:
            confirm_password = password
        csrf = self.get_csrf_token("/register")
        return self.client.post("/register", data={
            "csrf_token": csrf,
            "name": name,
            "mobile": mobile,
            "aadhaar": aadhaar,
            "village": village,
            "password": password,
            "confirm_password": confirm_password
        }, follow_redirects=True)

    # ==================================================
    # 1. FARMERS TESTS (1 - 7)
    # ==================================================

    def test_01_farmer_registration_succeeds(self):
        """1. Registration succeeds with valid details."""
        res = self.register_farmer()
        self.assertIn(b"Registration successful", res.data)
        farmer = db.query_db("SELECT * FROM farmers WHERE mobile = '9848011111'", one=True)
        self.assertIsNotNone(farmer)
        self.assertEqual(farmer["name"], "Varma")

    def test_02_duplicate_mobile_registration_rejected(self):
        """2. Duplicate mobile registration is rejected."""
        self.register_farmer(mobile="9848022222")
        res = self.register_farmer(mobile="9848022222", name="Another Farmer")
        self.assertIn(b"already registered", res.data)
        count = db.query_db("SELECT COUNT(*) FROM farmers WHERE mobile = '9848022222'", one=True)[0]
        self.assertEqual(count, 1)

    def test_03_invalid_mobile_rejected(self):
        """3. Invalid mobile numbers are rejected."""
        res = self.register_farmer(mobile="12345")
        self.assertIn(b"valid 10-digit mobile", res.data)
        count = db.query_db("SELECT COUNT(*) FROM farmers WHERE mobile = '12345'", one=True)[0]
        self.assertEqual(count, 0)

    def test_04_passwords_are_hashed(self):
        """4. Passwords are hashed and never stored in plaintext."""
        plain = "MySecretPass@123"
        self.register_farmer(mobile="9848033333", password=plain)
        farmer = db.query_db("SELECT * FROM farmers WHERE mobile = '9848033333'", one=True)
        self.assertNotEqual(farmer["password_hash"], plain)
        self.assertTrue(farmer["password_hash"].startswith(("scrypt:", "pbkdf2:")))
        self.assertTrue(auth.verify_password(plain, farmer["password_hash"]))

    def test_05_login_succeeds_with_correct_credentials(self):
        """5. Login succeeds with correct credentials and establishes farmer session."""
        self.register_farmer(mobile="9848044444", password="CorrectPassword@1")
        res = self.login_farmer(mobile="9848044444", password="CorrectPassword@1")
        self.assertIn(b"Farmer Dashboard", res.data)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("role"), "farmer")
            self.assertIsNotNone(sess.get("user_id"))

    def test_06_login_fails_with_incorrect_credentials(self):
        """6. Login fails with incorrect credentials."""
        self.register_farmer(mobile="9848055555", password="RealPassword@1")
        res = self.login_farmer(mobile="9848055555", password="WrongPassword!")
        self.assertIn(b"Invalid mobile number or password", res.data)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_07_logout_clears_session(self):
        """7. Logout clears the session completely."""
        self.register_farmer(mobile="9848066666", password="Password123")
        self.login_farmer(mobile="9848066666", password="Password123")
        res = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b"logged out", res.data)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))
            self.assertIsNone(sess.get("role"))

    # ==================================================
    # 2. RICE MILLS TESTS (8 - 15)
    # ==================================================

    def test_08_admin_can_add_rice_mill(self):
        """8. An administrator can add a rice mill."""
        self.login_admin()
        csrf = self.get_csrf_token("/admin/rice-mills/new")
        res = self.client.post("/admin/rice-mills/new", data={
            "csrf_token": csrf,
            "mill_name": "Test Modern Rice Mill Mandapeta",
            "location": "Canal Road, Mandapeta"
        }, follow_redirects=True)
        self.assertIn(b"added successfully", res.data)
        mill = db.query_db("SELECT * FROM rice_mills WHERE mill_name = 'Test Modern Rice Mill Mandapeta'", one=True)
        self.assertIsNotNone(mill)
        self.assertEqual(mill["is_active"], 1)

    def test_09_admin_can_edit_rice_mill(self):
        """9. An administrator can edit a rice mill."""
        self.login_admin()
        mill_id = db.query_db(
            "INSERT INTO rice_mills (mill_name, location, is_active, created_at, updated_at) VALUES ('Old Mill Name', 'Loc 1', 1, '2026-01-01', '2026-01-01')",
            commit=True
        )
        csrf = self.get_csrf_token(f"/admin/rice-mills/{mill_id}/edit")
        res = self.client.post(f"/admin/rice-mills/{mill_id}/edit", data={
            "csrf_token": csrf,
            "mill_name": "Updated Mill Name Mandapeta",
            "location": "Updated Location Bypass"
        }, follow_redirects=True)
        self.assertIn(b"updated successfully", res.data)
        updated = db.query_db("SELECT * FROM rice_mills WHERE id = ?", (mill_id,), one=True)
        self.assertEqual(updated["mill_name"], "Updated Mill Name Mandapeta")

    def test_10_admin_can_activate_deactivate_rice_mill(self):
        """10. An administrator can activate or deactivate a rice mill."""
        self.login_admin()
        mill_id = db.query_db(
            "INSERT INTO rice_mills (mill_name, location, is_active, created_at, updated_at) VALUES ('Toggle Mill', 'Loc', 1, '2026-01-01', '2026-01-01')",
            commit=True
        )
        csrf = self.get_csrf_token("/admin/rice-mills")
        # Deactivate
        self.client.post(f"/admin/rice-mills/{mill_id}/toggle", data={"csrf_token": csrf}, follow_redirects=True)
        mill = db.query_db("SELECT is_active FROM rice_mills WHERE id = ?", (mill_id,), one=True)
        self.assertEqual(mill["is_active"], 0)

        # Activate
        self.client.post(f"/admin/rice-mills/{mill_id}/toggle", data={"csrf_token": csrf}, follow_redirects=True)
        mill = db.query_db("SELECT is_active FROM rice_mills WHERE id = ?", (mill_id,), one=True)
        self.assertEqual(mill["is_active"], 1)

    def test_11_duplicate_rice_mill_names_handled(self):
        """11. Duplicate rice mill names are handled appropriately."""
        self.login_admin()
        csrf = self.get_csrf_token("/admin/rice-mills/new")
        self.client.post("/admin/rice-mills/new", data={
            "csrf_token": csrf,
            "mill_name": "Unique Mill Mandapeta",
            "location": "Loc 1"
        }, follow_redirects=True)
        res = self.client.post("/admin/rice-mills/new", data={
            "csrf_token": csrf,
            "mill_name": "unique mill mandapeta",
            "location": "Loc 2"
        }, follow_redirects=True)
        self.assertIn(b"already exists", res.data)

    def test_12_active_rice_mills_appear_in_dropdown(self):
        """12. Active rice mills appear in the farmer transaction dropdown."""
        self.register_farmer(mobile="9848077777")
        self.login_farmer(mobile="9848077777")
        db.query_db(
            "INSERT INTO rice_mills (mill_name, location, is_active, created_at, updated_at) VALUES ('Special Active Mill', 'Mandapeta', 1, '2026-01-01', '2026-01-01')",
            commit=True
        )
        res = self.client.get("/farmer/transactions/new")
        self.assertIn(b"Special Active Mill", res.data)

    def test_13_inactive_rice_mills_cannot_be_selected(self):
        """13. Inactive rice mills cannot be selected for new transactions."""
        self.register_farmer(mobile="9848088888")
        self.login_farmer(mobile="9848088888")
        inactive_id = db.query_db(
            "INSERT INTO rice_mills (mill_name, location, is_active, created_at, updated_at) VALUES ('Inactive Mill XYZ', 'Mandapeta', 0, '2026-01-01', '2026-01-01')",
            commit=True
        )
        res = self.client.get("/farmer/transactions/new")
        self.assertNotIn(b"Inactive Mill XYZ", res.data)

        csrf = self.get_csrf_token("/farmer/transactions/new")
        post_res = self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(inactive_id),
            "paddy_type": "BPT 5204",
            "number_of_bags": "100",
            "vehicle_number": "AP 31 TX 1111",
            "vehicle_weight_kg": "7500",
            "driver_mobile": "9848099999"
        }, follow_redirects=True)
        self.assertIn(b"inactive", post_res.data)

    def test_14_farmers_cannot_manage_rice_mills(self):
        """14. Farmers cannot manage rice mills."""
        self.register_farmer(mobile="9848091111")
        self.login_farmer(mobile="9848091111")
        res = self.client.get("/admin/rice-mills", follow_redirects=True)
        self.assertIn(b"Administrator authentication required", res.data)

    def test_15_invalid_rice_mill_ids_rejected(self):
        """15. Invalid rice mill IDs are rejected by the backend."""
        self.register_farmer(mobile="9848092222")
        self.login_farmer(mobile="9848092222")
        csrf = self.get_csrf_token("/farmer/transactions/new")
        res = self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": "999999",
            "paddy_type": "BPT 5204",
            "number_of_bags": "100",
            "vehicle_number": "AP 31 TX 2222",
            "vehicle_weight_kg": "7500",
            "driver_mobile": "9848099999"
        }, follow_redirects=True)
        self.assertIn(b"does not exist", res.data)

    # ==================================================
    # 3. TRANSACTIONS TESTS (16 - 27)
    # ==================================================

    def test_16_farmer_can_submit_valid_transaction(self):
        """16. A farmer can submit a valid transaction."""
        self.register_farmer(mobile="9848093333")
        self.login_farmer(mobile="9848093333")
        mill = db.query_db("SELECT id FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        res = self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "MTU 1010",
            "number_of_bags": "250",
            "vehicle_number": "AP 31 TX 5555",
            "vehicle_weight_kg": "18750",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        self.assertIn(b"submitted successfully", res.data)

    def test_17_transaction_receives_pending_status(self):
        """17. A new transaction receives PENDING status initially."""
        self.register_farmer(mobile="9848094444")
        self.login_farmer(mobile="9848094444")
        mill = db.query_db("SELECT id FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "Swarna",
            "number_of_bags": "300",
            "vehicle_number": "AP 31 TX 6666",
            "vehicle_weight_kg": "22500",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        tx = db.query_db("SELECT * FROM transactions WHERE vehicle_number = 'AP 31 TX 6666'", one=True)
        self.assertIsNotNone(tx)
        self.assertEqual(tx["status"], "PENDING")

    def test_18_unique_transaction_id_format_generated(self):
        """18. A unique transaction ID is generated in format SSC-YYYYMMDD-XXXXXXXX."""
        tx_id = auth.generate_transaction_id()
        today_str = datetime.datetime.now().strftime("%Y%m%d")
        self.assertTrue(tx_id.startswith(f"SSC-{today_str}-"))
        self.assertEqual(len(tx_id), 21)

    def test_19_selected_rice_mill_in_transaction_history(self):
        """19. The selected rice mill appears in transaction history."""
        self.register_farmer(mobile="9848095555")
        self.login_farmer(mobile="9848095555")
        mill = db.query_db("SELECT id, mill_name FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "BPT 5204",
            "number_of_bags": "150",
            "vehicle_number": "AP 31 TX 7777",
            "vehicle_weight_kg": "11250",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        history_res = self.client.get("/farmer/transactions")
        self.assertIn(mill["mill_name"].encode("utf-8"), history_res.data)

    def test_20_selected_rice_mill_in_transaction_details(self):
        """20. The selected rice mill appears in transaction details."""
        self.register_farmer(mobile="9848096666")
        self.login_farmer(mobile="9848096666")
        mill = db.query_db("SELECT id, mill_name FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "MTU 1061",
            "number_of_bags": "180",
            "vehicle_number": "AP 31 TX 8888",
            "vehicle_weight_kg": "13500",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        tx = db.query_db("SELECT transaction_id FROM transactions WHERE vehicle_number = 'AP 31 TX 8888'", one=True)
        detail_res = self.client.get(f"/farmer/transactions/{tx['transaction_id']}")
        self.assertIn(mill["mill_name"].encode("utf-8"), detail_res.data)

    def test_21_admin_can_approve_pending_transaction(self):
        """21. An administrator can approve a pending transaction."""
        self.register_farmer(mobile="9848097777")
        self.login_farmer(mobile="9848097777")
        mill = db.query_db("SELECT id FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "BPT 5204",
            "number_of_bags": "200",
            "vehicle_number": "AP 31 TX 9991",
            "vehicle_weight_kg": "15000",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        tx = db.query_db("SELECT transaction_id FROM transactions WHERE vehicle_number = 'AP 31 TX 9991'", one=True)
        tx_id = tx["transaction_id"]

        self.login_admin()
        csrf_admin = self.get_csrf_token(f"/admin/transactions/{tx_id}")
        res = self.client.post(f"/admin/transactions/{tx_id}/decision", data={
            "csrf_token": csrf_admin,
            "decision": "APPROVED"
        }, follow_redirects=True)
        self.assertIn(b"marked as APPROVED", res.data)
        updated_tx = db.query_db("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,), one=True)
        self.assertEqual(updated_tx["status"], "APPROVED")
        self.assertIsNotNone(updated_tx["decision_timestamp"])
        self.assertIsNotNone(updated_tx["decided_by_admin_id"])

    def test_22_admin_can_reject_pending_transaction(self):
        """22. An administrator can reject a pending transaction."""
        self.register_farmer(mobile="9848098888")
        self.login_farmer(mobile="9848098888")
        mill = db.query_db("SELECT id FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "Swarna",
            "number_of_bags": "220",
            "vehicle_number": "AP 31 TX 9992",
            "vehicle_weight_kg": "16500",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        tx = db.query_db("SELECT transaction_id FROM transactions WHERE vehicle_number = 'AP 31 TX 9992'", one=True)
        tx_id = tx["transaction_id"]

        self.login_admin()
        csrf_admin = self.get_csrf_token(f"/admin/transactions/{tx_id}")
        res = self.client.post(f"/admin/transactions/{tx_id}/decision", data={
            "csrf_token": csrf_admin,
            "decision": "REJECTED",
            "rejection_reason": "High moisture content above 18%"
        }, follow_redirects=True)
        self.assertIn(b"marked as REJECTED", res.data)
        updated_tx = db.query_db("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,), one=True)
        self.assertEqual(updated_tx["status"], "REJECTED")

    def test_23_rejection_reasons_saved_and_displayed(self):
        """23. Rejection reasons are saved and displayed to the farmer."""
        self.register_farmer(mobile="9848099991")
        self.login_farmer(mobile="9848099991")
        mill = db.query_db("SELECT id FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "BPT 5204",
            "number_of_bags": "100",
            "vehicle_number": "AP 31 TX 9993",
            "vehicle_weight_kg": "7500",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        tx = db.query_db("SELECT transaction_id FROM transactions WHERE vehicle_number = 'AP 31 TX 9993'", one=True)
        tx_id = tx["transaction_id"]

        self.login_admin()
        csrf_admin = self.get_csrf_token(f"/admin/transactions/{tx_id}")
        self.client.post(f"/admin/transactions/{tx_id}/decision", data={
            "csrf_token": csrf_admin,
            "decision": "REJECTED",
            "rejection_reason": "Discoloration and broken grains"
        }, follow_redirects=True)

        self.login_farmer(mobile="9848099991")
        detail_res = self.client.get(f"/farmer/transactions/{tx_id}")
        self.assertIn(b"Discoloration and broken grains", detail_res.data)

    def test_24_repeated_decisions_prevented(self):
        """24. Repeated or conflicting decisions on already processed transactions are prevented."""
        self.register_farmer(mobile="9848099992")
        self.login_farmer(mobile="9848099992")
        mill = db.query_db("SELECT id FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "BPT 5204",
            "number_of_bags": "100",
            "vehicle_number": "AP 31 TX 9994",
            "vehicle_weight_kg": "7500",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        tx = db.query_db("SELECT transaction_id FROM transactions WHERE vehicle_number = 'AP 31 TX 9994'", one=True)
        tx_id = tx["transaction_id"]

        # Decision 1: Approve
        self.login_admin()
        csrf_admin = self.get_csrf_token(f"/admin/transactions/{tx_id}")
        self.client.post(f"/admin/transactions/{tx_id}/decision", data={
            "csrf_token": csrf_admin,
            "decision": "APPROVED"
        }, follow_redirects=True)

        # Decision 2: Attempt repeated decision (Reject)
        res = self.client.post(f"/admin/transactions/{tx_id}/decision", data={
            "csrf_token": csrf_admin,
            "decision": "REJECTED"
        }, follow_redirects=True)
        self.assertIn(b"Repeated decisions are prevented", res.data)
        tx_check = db.query_db("SELECT status FROM transactions WHERE transaction_id = ?", (tx_id,), one=True)
        self.assertEqual(tx_check["status"], "APPROVED")

    def test_25_farmers_cannot_access_other_farmer_transactions(self):
        """25. Farmers cannot access another farmer's transactions."""
        self.register_farmer(mobile="9848099993", name="Farmer One")
        self.login_farmer(mobile="9848099993")
        mill = db.query_db("SELECT id FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "BPT 5204",
            "number_of_bags": "100",
            "vehicle_number": "AP 31 TX 9995",
            "vehicle_weight_kg": "7500",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        tx = db.query_db("SELECT transaction_id FROM transactions WHERE vehicle_number = 'AP 31 TX 9995'", one=True)
        tx_id = tx["transaction_id"]

        self.register_farmer(mobile="9848099994", name="Farmer Two")
        self.login_farmer(mobile="9848099994")
        res = self.client.get(f"/farmer/transactions/{tx_id}", follow_redirects=True)
        self.assertIn(b"do not have permission", res.data)

    def test_26_farmers_cannot_approve_transactions(self):
        """26. Farmers cannot approve transactions."""
        self.register_farmer(mobile="9848099995")
        self.login_farmer(mobile="9848099995")
        mill = db.query_db("SELECT id FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "BPT 5204",
            "number_of_bags": "100",
            "vehicle_number": "AP 31 TX 9996",
            "vehicle_weight_kg": "7500",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        tx = db.query_db("SELECT transaction_id FROM transactions WHERE vehicle_number = 'AP 31 TX 9996'", one=True)
        tx_id = tx["transaction_id"]

        res = self.client.post(f"/admin/transactions/{tx_id}/decision", data={
            "decision": "APPROVED"
        }, follow_redirects=True)
        self.assertIn(b"Administrator authentication required", res.data)
        tx_check = db.query_db("SELECT status FROM transactions WHERE transaction_id = ?", (tx_id,), one=True)
        self.assertEqual(tx_check["status"], "PENDING")

    def test_27_admin_search_and_filters_work(self):
        """27. Admin search and filters work correctly."""
        self.register_farmer(mobile="9848099996", name="UniqueSearchFarmer")
        self.login_farmer(mobile="9848099996")
        mill = db.query_db("SELECT id FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "RNR 15048",
            "number_of_bags": "120",
            "vehicle_number": "AP 31 FINDME",
            "vehicle_weight_kg": "9000",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)

        self.login_admin()
        search_res = self.client.get("/admin/transactions?search=FINDME")
        self.assertIn(b"AP 31 FINDME", search_res.data)
        no_res = self.client.get("/admin/transactions?search=NONEXISTENT123")
        self.assertNotIn(b"AP 31 FINDME", no_res.data)

    # ==================================================
    # 4. RECEIPTS & QR VERIFICATION TESTS (28 - 33)
    # ==================================================

    def test_28_approved_transactions_have_receipts(self):
        """28. Approved transactions have downloadable/viewable receipts."""
        self.register_farmer(mobile="9848099997")
        self.login_farmer(mobile="9848099997")
        mill = db.query_db("SELECT id FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "BPT 5204",
            "number_of_bags": "100",
            "vehicle_number": "AP 31 RECEIPT1",
            "vehicle_weight_kg": "7500",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        tx = db.query_db("SELECT transaction_id FROM transactions WHERE vehicle_number = 'AP 31 RECEIPT1'", one=True)
        tx_id = tx["transaction_id"]

        self.login_admin()
        csrf_admin = self.get_csrf_token(f"/admin/transactions/{tx_id}")
        self.client.post(f"/admin/transactions/{tx_id}/decision", data={
            "csrf_token": csrf_admin,
            "decision": "APPROVED"
        }, follow_redirects=True)

        self.login_farmer(mobile="9848099997")
        res = self.client.get(f"/receipt/{tx_id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"OFFICIAL PADDY CANVASING MEMO / RECEIPT", res.data)
        self.assertIn(b"SRI SRINIVASA CANVASING", res.data)

    def test_29_receipts_display_correct_rice_mill_name(self):
        """29. Receipts display the correct rice mill name."""
        self.register_farmer(mobile="9848099998")
        self.login_farmer(mobile="9848099998")
        mill = db.query_db("SELECT id, mill_name FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "BPT 5204",
            "number_of_bags": "100",
            "vehicle_number": "AP 31 RECEIPT2",
            "vehicle_weight_kg": "7500",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        tx = db.query_db("SELECT transaction_id FROM transactions WHERE vehicle_number = 'AP 31 RECEIPT2'", one=True)
        tx_id = tx["transaction_id"]

        self.login_admin()
        csrf_admin = self.get_csrf_token(f"/admin/transactions/{tx_id}")
        self.client.post(f"/admin/transactions/{tx_id}/decision", data={
            "csrf_token": csrf_admin,
            "decision": "APPROVED"
        }, follow_redirects=True)

        res = self.client.get(f"/receipt/{tx_id}")
        self.assertIn(mill["mill_name"].encode("utf-8"), res.data)

    def test_30_historical_receipts_without_rice_mill_accessible(self):
        """30. Historical receipts without a rice mill remain accessible and display 'Not recorded'."""
        farmer_id = db.query_db(
            "INSERT INTO farmers (name, mobile, aadhaar, village, password_hash, created_at) VALUES ('Old Farmer', '9848000001', '123456789012', 'Mandapeta', 'hash', '2025-01-01')",
            commit=True
        )
        tx_id = "SSC-20250101-HIST0001"
        db.query_db(
            """
            INSERT INTO transactions (
                transaction_id, farmer_id, rice_mill_id, rice_mill_name_snapshot,
                paddy_type, number_of_bags, vehicle_number, vehicle_weight_kg,
                driver_mobile, transaction_timestamp, status, created_at
            )
            VALUES (?, ?, NULL, NULL, 'BPT 5204', 100, 'AP 31 OLD 01', 7500, '9848077777', '2025-01-01 10:00:00', 'APPROVED', '2025-01-01')
            """,
            (tx_id, farmer_id),
            commit=True
        )
        self.login_admin()
        res = self.client.get(f"/receipt/{tx_id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Not recorded", res.data)

    def test_31_qr_verification_retrieves_correct_transaction(self):
        """31. QR verification retrieves the correct transaction live from database."""
        self.register_farmer(mobile="9848000002")
        self.login_farmer(mobile="9848000002")
        mill = db.query_db("SELECT id FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        csrf = self.get_csrf_token("/farmer/transactions/new")
        self.client.post("/farmer/transactions/new", data={
            "csrf_token": csrf,
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "Super Fine Raw",
            "number_of_bags": "500",
            "vehicle_number": "AP 31 QRVERIFY",
            "vehicle_weight_kg": "37500",
            "driver_mobile": "9848077777"
        }, follow_redirects=True)
        tx = db.query_db("SELECT transaction_id FROM transactions WHERE vehicle_number = 'AP 31 QRVERIFY'", one=True)
        tx_id = tx["transaction_id"]

        self.client.get("/logout")
        res = self.client.get(f"/verify/{tx_id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Transaction Verification", res.data)
        self.assertIn(tx_id.encode("utf-8"), res.data)
        self.assertIn(b"Super Fine Raw", res.data)
        self.assertIn(b"500 bags", res.data)

    def test_32_sensitive_info_not_exposed_through_qr_verification(self):
        """32. Sensitive information (Aadhaar, passwords, full mobile) is NOT exposed via QR verification."""
        f_id = db.query_db(
            "INSERT INTO farmers (name, mobile, aadhaar, village, password_hash, created_at) VALUES ('Confidential Farmer', '9848099999', '999988887777', 'Mandapeta', 'secret_hash_value', '2026-01-01')",
            commit=True
        )
        tx_id = "SSC-20260101-CONF0001"
        db.query_db(
            """
            INSERT INTO transactions (
                transaction_id, farmer_id, rice_mill_id, rice_mill_name_snapshot,
                paddy_type, number_of_bags, vehicle_number, vehicle_weight_kg,
                driver_mobile, transaction_timestamp, status, created_at
            )
            VALUES (?, ?, NULL, 'Mill Alpha', 'BPT 5204', 100, 'AP 31 PRIVACY', 7500, '9848077777', '2026-01-01 10:00:00', 'APPROVED', '2026-01-01')
            """,
            (tx_id, f_id),
            commit=True
        )
        res = self.client.get(f"/verify/{tx_id}")
        self.assertNotIn(b"999988887777", res.data)
        self.assertNotIn(b"secret_hash_value", res.data)
        self.assertNotIn(b"9848077777", res.data)

    def test_33_print_styles_hide_navigation_and_buttons(self):
        """33. Print stylesheet exists and hides navigation and action buttons."""
        print_css_path = os.path.join(PROJECT_DIR, "static", "css", "print.css")
        self.assertTrue(os.path.exists(print_css_path))
        with open(print_css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        self.assertIn("display: none !important", css_content)
        self.assertIn(".navbar", css_content)
        self.assertIn(".btn", css_content)
        self.assertIn("@page", css_content)

    # ==================================================
    # 5. DATABASE INTEGRITY TESTS (34 - 37)
    # ==================================================

    def test_34_existing_records_remain_intact_after_migration(self):
        """34. Existing records remain intact after running migrations multiple times."""
        f_id = db.query_db(
            "INSERT INTO farmers (name, mobile, aadhaar, village, password_hash, created_at) VALUES ('Persistent Farmer', '9848012399', '123412341234', 'Mandapeta', 'hashed_pass', '2026-01-01')",
            commit=True
        )
        db.migrate_and_init_db()
        db.migrate_and_init_db()

        farmer = db.query_db("SELECT * FROM farmers WHERE id = ?", (f_id,), one=True)
        self.assertIsNotNone(farmer)
        self.assertEqual(farmer["name"], "Persistent Farmer")
        self.assertEqual(farmer["mobile"], "9848012399")

    def test_35_transactions_persist_across_connections(self):
        """35. Transactions persist after closing and reopening database connections."""
        f_id = db.query_db(
            "INSERT INTO farmers (name, mobile, aadhaar, village, password_hash, created_at) VALUES ('Persistence Test', '9848099887', '123456789012', 'Mandapeta', 'hash', '2026-01-01')",
            commit=True
        )
        tx_id = "SSC-20261026-PERSIST1"
        db.query_db(
            """
            INSERT INTO transactions (
                transaction_id, farmer_id, paddy_type, number_of_bags, vehicle_number,
                vehicle_weight_kg, driver_mobile, transaction_timestamp, status, created_at
            )
            VALUES (?, ?, 'BPT 5204', 100, 'AP 31 TEST 99', 7500, '9848077777', '2026-10-26 10:00:00', 'PENDING', '2026-10-26')
            """,
            (tx_id, f_id),
            commit=True
        )

        new_conn = sqlite3.connect(self.db_path)
        new_conn.row_factory = sqlite3.Row
        cur = new_conn.cursor()
        cur.execute("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,))
        row = cur.fetchone()
        new_conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row["transaction_id"], tx_id)
        self.assertEqual(row["status"], "PENDING")

    def test_36_foreign_key_constraints(self):
        """36. Foreign key constraints enforce referential integrity."""
        with self.assertRaises(Exception):
            db.query_db(
                """
                INSERT INTO transactions (
                    transaction_id, farmer_id, paddy_type, number_of_bags, vehicle_number,
                    vehicle_weight_kg, driver_mobile, transaction_timestamp, status, created_at
                )
                VALUES ('SSC-TEST-INVALID-FK', 999999, 'BPT 5204', 100, 'AP 31 FK 01', 7500, '9848077777', '2026-01-01', 'PENDING', '2026-01-01')
                """,
                commit=True
            )

    def test_37_database_errors_handled_safely(self):
        """37. Database errors are handled safely and trigger rollback."""
        tx_id = "SSC-COLLISION-TEST"
        f_id = db.query_db(
            "INSERT INTO farmers (name, mobile, aadhaar, village, password_hash, created_at) VALUES ('Error Farmer', '9848011223', '123456789012', 'Mandapeta', 'hash', '2026-01-01')",
            commit=True
        )
        db.query_db(
            """
            INSERT INTO transactions (
                transaction_id, farmer_id, paddy_type, number_of_bags, vehicle_number,
                vehicle_weight_kg, driver_mobile, transaction_timestamp, status, created_at
            )
            VALUES (?, ?, 'BPT 5204', 100, 'AP 31 ERR 01', 7500, '9848077777', '2026-01-01', 'PENDING', '2026-01-01')
            """,
            (tx_id, f_id),
            commit=True
        )

        with self.assertRaises(Exception):
            db.query_db(
                """
                INSERT INTO transactions (
                    transaction_id, farmer_id, paddy_type, number_of_bags, vehicle_number,
                    vehicle_weight_kg, driver_mobile, transaction_timestamp, status, created_at
                )
                VALUES (?, ?, 'BPT 5204', 100, 'AP 31 ERR 02', 7500, '9848077777', '2026-01-01', 'PENDING', '2026-01-01')
                """,
                (tx_id, f_id),
                commit=True
            )



    def test_38_admin_marks_payment_completed_and_farmer_views_it(self):
        """38. Admin marks payment as COMPLETED and farmer sees Paid status across views."""
        # Register and login farmer
        self.register_farmer("Payment Farmer", "9848099881", "123456789012", "Mandapeta", "Pass@12345")
        self.login_farmer("9848099881", "Pass@12345")
        
        mill = db.query_db("SELECT id FROM rice_mills WHERE is_active = 1 LIMIT 1", one=True)
        # Create a transaction
        tx_resp = self.client.post("/farmer/transactions/new", data={
            "csrf_token": "test-csrf-token",
            "rice_mill_id": str(mill["id"]),
            "paddy_type": "1061",
            "number_of_bags": "150",
            "vehicle_number": "AP 05 TX 9999",
            "vehicle_weight_kg": "11250",
            "driver_mobile": "9848012345"
        }, follow_redirects=True)
        self.assertEqual(tx_resp.status_code, 200)

        # Retrieve created transaction ID
        row = db.query_db("SELECT transaction_id, payment_status FROM transactions WHERE vehicle_number = 'AP 05 TX 9999'", one=True)
        self.assertIsNotNone(row)
        tx_id = row["transaction_id"]
        self.assertEqual(row["payment_status"], "PENDING")

        # Admin logs in and approves transaction
        self.login_admin()
        dec_resp = self.client.post(f"/admin/transactions/{tx_id}/decision", data={
            "csrf_token": "test-csrf-token",
            "decision": "APPROVED"
        }, follow_redirects=True)
        self.assertEqual(dec_resp.status_code, 200)

        # Admin marks payment completed
        pay_resp = self.client.post(f"/admin/transactions/{tx_id}/payment", data={
            "csrf_token": "test-csrf-token",
            "payment_status": "COMPLETED",
            "payment_notes": "UTR: SBI123456789 - Transferred to SBI Mandapeta"
        }, follow_redirects=True)
        self.assertEqual(pay_resp.status_code, 200)
        self.assertIn(b"Payment marked as COMPLETED", pay_resp.data)

        # Verify in database
        tx_updated = db.query_db("SELECT payment_status, payment_notes, payment_timestamp FROM transactions WHERE transaction_id = ?", (tx_id,), one=True)
        self.assertEqual(tx_updated["payment_status"], "COMPLETED")
        self.assertIn("SBI123456789", tx_updated["payment_notes"])
        self.assertIsNotNone(tx_updated["payment_timestamp"])

        # Farmer logs in and checks views
        self.login_farmer("9848099881", "Pass@12345")

        # 1. Farmer dashboard displays Completed Payments
        dash_resp = self.client.get("/farmer/dashboard")
        self.assertEqual(dash_resp.status_code, 200)
        self.assertIn(b"Payments Completed", dash_resp.data)
        self.assertIn(b"Completed", dash_resp.data)

        # 2. Farmer transaction history displays Payment Status
        hist_resp = self.client.get("/farmer/transactions")
        self.assertEqual(hist_resp.status_code, 200)
        self.assertIn(b"Completed", hist_resp.data)

        # 3. Transaction details displays payment settlement notice
        details_resp = self.client.get(f"/farmer/transactions/{tx_id}")
        self.assertEqual(details_resp.status_code, 200)
        self.assertIn(b"Payment Has Been Completed", details_resp.data)
        self.assertIn(b"SBI123456789", details_resp.data)

        # 4. Receipt displays payment status COMPLETED
        receipt_resp = self.client.get(f"/receipt/{tx_id}")
        self.assertEqual(receipt_resp.status_code, 200)
        self.assertIn(b"COMPLETED", receipt_resp.data)

    def test_39_farmer_cannot_alter_payment_status(self):
        """39. Farmers and unauthorized users cannot modify payment status."""
        self.register_farmer("Unauthorized Farmer", "9848099882", "123456789013", "Mandapeta", "Pass@12345")
        self.login_farmer("9848099882", "Pass@12345")

        tx_id = "SSC-PAYMENT-AUTH-TEST"
        f_row = db.query_db("SELECT id FROM farmers WHERE mobile = '9848099882'", one=True)
        db.query_db(
            """
            INSERT INTO transactions (
                transaction_id, farmer_id, paddy_type, number_of_bags, vehicle_number,
                vehicle_weight_kg, driver_mobile, transaction_timestamp, status, payment_status, created_at
            )
            VALUES (?, ?, 'BPT 5204', 100, 'AP 05 AUTH 1', 7500, '9848077777', '2026-01-01', 'APPROVED', 'PENDING', '2026-01-01')
            """,
            (tx_id, f_row["id"]),
            commit=True
        )

        # Attempt to post as farmer to admin payment endpoint
        resp = self.client.post(f"/admin/transactions/{tx_id}/payment", data={
            "csrf_token": "test-csrf-token",
            "payment_status": "COMPLETED"
        }, follow_redirects=True)

        # Should be redirected to admin login
        self.assertIn(b"Administrator Login", resp.data)

        # Database record should remain PENDING
        tx_row = db.query_db("SELECT payment_status FROM transactions WHERE transaction_id = ?", (tx_id,), one=True)
        self.assertEqual(tx_row["payment_status"], "PENDING")

    def test_40_admin_can_revert_payment_to_pending(self):
        """40. Admin can revert payment status back to PENDING if necessary."""
        tx_id = "SSC-PAYMENT-REVERT-TEST"
        f_id = db.query_db(
            "INSERT INTO farmers (name, mobile, aadhaar, village, password_hash, created_at) VALUES ('Revert Farmer', '9848099883', '123456789014', 'Mandapeta', 'hash', '2026-01-01')",
            commit=True
        )
        db.query_db(
            """
            INSERT INTO transactions (
                transaction_id, farmer_id, paddy_type, number_of_bags, vehicle_number,
                vehicle_weight_kg, driver_mobile, transaction_timestamp, status, payment_status, created_at
            )
            VALUES (?, ?, 'BPT 5204', 100, 'AP 05 REV 1', 7500, '9848077777', '2026-01-01', 'APPROVED', 'COMPLETED', '2026-01-01')
            """,
            (tx_id, f_id),
            commit=True
        )

        self.login_admin()
        resp = self.client.post(f"/admin/transactions/{tx_id}/payment", data={
            "csrf_token": "test-csrf-token",
            "payment_status": "PENDING",
            "payment_notes": "Payment hold requested"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        tx_row = db.query_db("SELECT payment_status, payment_notes, payment_timestamp FROM transactions WHERE transaction_id = ?", (tx_id,), one=True)
        self.assertEqual(tx_row["payment_status"], "PENDING")
        self.assertIsNone(tx_row["payment_timestamp"])

if __name__ == "__main__":
    unittest.main()
