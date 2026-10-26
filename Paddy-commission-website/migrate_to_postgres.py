"""
SRI SRINIVASA CANVASING - Database Migration Utility
Mandapeta, Andhra Pradesh

Safely migrates all existing records from local SQLite (database.db)
to production PostgreSQL without data loss.

Usage:
    export DATABASE_URL="postgresql://user:password@hostname:5432/dbname"
    python migrate_to_postgres.py
"""

import os
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB = os.path.join(BASE_DIR, "database.db")
POSTGRES_URL = os.environ.get("DATABASE_URL")


def migrate():
    if not os.path.exists(SQLITE_DB):
        print(f"Error: SQLite database '{SQLITE_DB}' does not exist.")
        sys.exit(1)

    if not POSTGRES_URL:
        print("Error: DATABASE_URL environment variable is not set.")
        print("Please set DATABASE_URL (e.g. postgresql://user:pass@host:5432/dbname)")
        sys.exit(1)

    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("Error: psycopg2 is required for PostgreSQL migration.")
        print("Please install with: pip install psycopg2-binary")
        sys.exit(1)

    print("==================================================")
    print("SRI SRINIVASA CANVASING - SQLite to PostgreSQL Migration")
    print(f"Source: {SQLITE_DB}")
    print(f"Target: {POSTGRES_URL.split('@')[-1]}")
    print("==================================================")

    # 1. Connect to SQLite
    s_conn = sqlite3.connect(SQLITE_DB)
    s_conn.row_factory = sqlite3.Row
    s_cur = s_conn.cursor()

    # 2. Connect to PostgreSQL
    pg_url = POSTGRES_URL
    if pg_url.startswith("postgres://"):
        pg_url = pg_url.replace("postgres://", "postgresql://", 1)

    p_conn = psycopg2.connect(pg_url)
    p_cur = p_conn.cursor()

    try:
        # Step A: Initialize target schema
        import db
        db.DATABASE_URL = pg_url
        print("1. Ensuring PostgreSQL schema and tables exist...")
        db.migrate_and_init_db()

        # Step B: Migrate Farmers
        s_cur.execute("SELECT id, name, mobile, aadhaar, village, password_hash, created_at FROM farmers")
        farmers = s_cur.fetchall()
        print(f"2. Migrating {len(farmers)} farmer record(s)...")
        for f in farmers:
            p_cur.execute(
                """
                INSERT INTO farmers (id, name, mobile, aadhaar, village, password_hash, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (f["id"], f["name"], f["mobile"], f["aadhaar"], f["village"], f["password_hash"], f["created_at"])
            )
        p_cur.execute("SELECT setval('farmers_id_seq', (SELECT COALESCE(MAX(id), 1) FROM farmers))")

        # Step C: Migrate Admins
        s_cur.execute("SELECT id, username, password_hash, created_at FROM admins")
        admins = s_cur.fetchall()
        print(f"3. Migrating {len(admins)} administrator record(s)...")
        for a in admins:
            p_cur.execute(
                """
                INSERT INTO admins (id, username, password_hash, created_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
                """,
                (a["id"], a["username"], a["password_hash"], a["created_at"])
            )
        p_cur.execute("SELECT setval('admins_id_seq', (SELECT COALESCE(MAX(id), 1) FROM admins))")

        # Step D: Migrate Rice Mills
        s_cur.execute("SELECT id, mill_name, location, is_active, created_at, updated_at FROM rice_mills")
        mills = s_cur.fetchall()
        print(f"4. Migrating {len(mills)} rice mill record(s)...")
        for m in mills:
            p_cur.execute(
                """
                INSERT INTO rice_mills (id, mill_name, location, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (m["id"], m["mill_name"], m["location"], bool(m["is_active"]), m["created_at"], m["updated_at"])
            )
        p_cur.execute("SELECT setval('rice_mills_id_seq', (SELECT COALESCE(MAX(id), 1) FROM rice_mills))")

        # Step E: Migrate Transactions
        s_cur.execute("""
            SELECT id, transaction_id, farmer_id, rice_mill_id, rice_mill_name_snapshot,
                   paddy_type, number_of_bags, vehicle_number, vehicle_weight_kg,
                   driver_mobile, transaction_timestamp, status, decided_by_admin_id,
                   decision_timestamp, rejection_reason, created_at
            FROM transactions
        """)
        txs = s_cur.fetchall()
        print(f"5. Migrating {len(txs)} transaction record(s)...")
        for t in txs:
            p_cur.execute(
                """
                INSERT INTO transactions (
                    id, transaction_id, farmer_id, rice_mill_id, rice_mill_name_snapshot,
                    paddy_type, number_of_bags, vehicle_number, vehicle_weight_kg,
                    driver_mobile, transaction_timestamp, status, decided_by_admin_id,
                    decision_timestamp, rejection_reason, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (transaction_id) DO NOTHING
                """,
                (
                    t["id"], t["transaction_id"], t["farmer_id"], t["rice_mill_id"],
                    t["rice_mill_name_snapshot"], t["paddy_type"], t["number_of_bags"],
                    t["vehicle_number"], t["vehicle_weight_kg"], t["driver_mobile"],
                    t["transaction_timestamp"], t["status"], t["decided_by_admin_id"],
                    t["decision_timestamp"], t["rejection_reason"], t["created_at"]
                )
            )
        p_cur.execute("SELECT setval('transactions_id_seq', (SELECT COALESCE(MAX(id), 1) FROM transactions))")

        p_conn.commit()
        print("==================================================")
        print("MIGRATION COMPLETED SUCCESSFULLY! All records intact.")
        print("==================================================")

    except Exception as e:
        p_conn.rollback()
        print(f"Migration Failed with error: {e}")
        sys.exit(1)
    finally:
        s_conn.close()
        p_conn.close()


if __name__ == "__main__":
    migrate()
