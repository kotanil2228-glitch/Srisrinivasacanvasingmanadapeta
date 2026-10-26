"""
SRI SRINIVASA CANVASING - Database Layer
Mandapeta, East Godavari District, Andhra Pradesh
Supports SQLite (local development) and PostgreSQL (production).
Provides non-destructive schema migrations and connection management.
"""

import os
import sqlite3
import datetime
from werkzeug.security import generate_password_hash

DATABASE_URL = os.environ.get("DATABASE_URL")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "database.db")


def is_postgres():
    return bool(DATABASE_URL and DATABASE_URL.startswith(("postgres://", "postgresql://")))


def get_db():
    """
    Returns a database connection with dict-like row access.
    """
    if is_postgres():
        import psycopg2
        import psycopg2.extras
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.DictCursor)
        conn.autocommit = False
        return conn
    else:
        db_path = os.environ.get("SQLITE_PATH", DEFAULT_SQLITE_PATH)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


def query_db(query, args=(), one=False, commit=False):
    """
    Execute a parameterized SQL query safely across SQLite and PostgreSQL.
    Converts '?' to '%s' when targeting PostgreSQL.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        actual_query = query
        if is_postgres():
            actual_query = query.replace("?", "%s")
        
        cur.execute(actual_query, args)
        if commit:
            conn.commit()
            last_id = getattr(cur, "lastrowid", None)
            cur.close()
            conn.close()
            return last_id

        rv = cur.fetchall()
        cur.close()
        conn.close()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        if commit and conn:
            try:
                conn.rollback()
            except Exception:
                pass
        if conn:
            conn.close()
        raise e


def migrate_and_init_db():
    """
    Idempotent, non-destructive migration and initialization:
    - Preserves existing records in farmers, admins, rice_mills, and transactions.
    - Safely adds missing columns (password_hash, created_at, payment_status, payment_timestamp, payment_notes).
    - Hashes any plaintext passwords found in legacy records.
    - Creates rice_mills and transactions tables with appropriate constraints.
    - Seeds default rice mills and admin if tables are empty.
    """
    conn = get_db()
    cur = conn.cursor()

    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        if not is_postgres():
            # 1. FARMERS TABLE
            cur.execute("""
            CREATE TABLE IF NOT EXISTS farmers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                mobile TEXT UNIQUE,
                aadhaar TEXT,
                village TEXT,
                password TEXT,
                password_hash TEXT,
                created_at TEXT
            )
            """)

            cur.execute("PRAGMA table_info(farmers)")
            existing_farmer_cols = [row[1] for row in cur.fetchall()]

            if "password_hash" not in existing_farmer_cols:
                cur.execute("ALTER TABLE farmers ADD COLUMN password_hash TEXT")
            if "created_at" not in existing_farmer_cols:
                cur.execute("ALTER TABLE farmers ADD COLUMN created_at TEXT")

            cur.execute("SELECT id, password, password_hash FROM farmers")
            for row in cur.fetchall():
                f_id = row[0]
                plain = row[1]
                hashed = row[2]
                if plain and not hashed:
                    new_hash = generate_password_hash(plain)
                    cur.execute("UPDATE farmers SET password_hash = ? WHERE id = ?", (new_hash, f_id))

            # 2. ADMINS TABLE
            cur.execute("""
            CREATE TABLE IF NOT EXISTS admins(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                password_hash TEXT,
                created_at TEXT
            )
            """)

            cur.execute("PRAGMA table_info(admins)")
            existing_admin_cols = [row[1] for row in cur.fetchall()]
            if "password_hash" not in existing_admin_cols:
                cur.execute("ALTER TABLE admins ADD COLUMN password_hash TEXT")
            if "created_at" not in existing_admin_cols:
                cur.execute("ALTER TABLE admins ADD COLUMN created_at TEXT")

            cur.execute("SELECT id, password, password_hash FROM admins")
            for row in cur.fetchall():
                a_id = row[0]
                plain = row[1]
                hashed = row[2]
                if plain and not hashed:
                    new_hash = generate_password_hash(plain)
                    cur.execute("UPDATE admins SET password_hash = ? WHERE id = ?", (new_hash, a_id))

            # 3. RICE MILLS TABLE
            cur.execute("""
            CREATE TABLE IF NOT EXISTS rice_mills(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mill_name TEXT NOT NULL,
                location TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

            # 4. TRANSACTIONS TABLE
            cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                farmer_id INTEGER NOT NULL,
                rice_mill_id INTEGER,
                rice_mill_name_snapshot TEXT,
                paddy_type TEXT NOT NULL,
                number_of_bags INTEGER NOT NULL,
                vehicle_number TEXT NOT NULL,
                vehicle_weight_kg REAL NOT NULL,
                driver_mobile TEXT NOT NULL,
                transaction_timestamp TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                decided_by_admin_id INTEGER,
                decision_timestamp TEXT,
                rejection_reason TEXT,
                payment_status TEXT NOT NULL DEFAULT 'PENDING',
                payment_timestamp TEXT,
                payment_notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (farmer_id) REFERENCES farmers(id) ON DELETE RESTRICT,
                FOREIGN KEY (rice_mill_id) REFERENCES rice_mills(id) ON DELETE SET NULL,
                FOREIGN KEY (decided_by_admin_id) REFERENCES admins(id) ON DELETE SET NULL
            )
            """)

            # Check existing columns in transactions for non-destructive upgrades
            cur.execute("PRAGMA table_info(transactions)")
            existing_tx_cols = [row[1] for row in cur.fetchall()]

            if "payment_status" not in existing_tx_cols:
                cur.execute("ALTER TABLE transactions ADD COLUMN payment_status TEXT DEFAULT 'PENDING'")
            if "payment_timestamp" not in existing_tx_cols:
                cur.execute("ALTER TABLE transactions ADD COLUMN payment_timestamp TEXT")
            if "payment_notes" not in existing_tx_cols:
                cur.execute("ALTER TABLE transactions ADD COLUMN payment_notes TEXT")

            # Indexes for performance and quick searching
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_farmer ON transactions(farmer_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_status ON transactions(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_id ON transactions(transaction_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_mill ON transactions(rice_mill_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_mills_active ON rice_mills(is_active)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_payment ON transactions(payment_status)")

        else:
            # PostgreSQL schema
            cur.execute("""
            CREATE TABLE IF NOT EXISTS farmers(
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                mobile VARCHAR(15) UNIQUE NOT NULL,
                aadhaar VARCHAR(20) NOT NULL,
                village VARCHAR(100) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS admins(
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS rice_mills(
                id SERIAL PRIMARY KEY,
                mill_name VARCHAR(200) NOT NULL,
                location VARCHAR(200),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS transactions(
                id SERIAL PRIMARY KEY,
                transaction_id VARCHAR(50) UNIQUE NOT NULL,
                farmer_id INTEGER NOT NULL REFERENCES farmers(id),
                rice_mill_id INTEGER REFERENCES rice_mills(id) ON DELETE SET NULL,
                rice_mill_name_snapshot VARCHAR(200),
                paddy_type VARCHAR(100) NOT NULL,
                number_of_bags INTEGER NOT NULL,
                vehicle_number VARCHAR(50) NOT NULL,
                vehicle_weight_kg NUMERIC(10,2) NOT NULL,
                driver_mobile VARCHAR(15) NOT NULL,
                transaction_timestamp TIMESTAMP NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                decided_by_admin_id INTEGER REFERENCES admins(id),
                decision_timestamp TIMESTAMP,
                rejection_reason TEXT,
                payment_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                payment_timestamp TIMESTAMP,
                payment_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_tx_farmer ON transactions(farmer_id);
            CREATE INDEX IF NOT EXISTS idx_tx_status ON transactions(status);
            CREATE INDEX IF NOT EXISTS idx_tx_id ON transactions(transaction_id);
            """)

        conn.commit()

        # Seed initial admin if none exists
        cur.execute("SELECT COUNT(*) FROM admins")
        admin_count = cur.fetchone()[0]
        if admin_count == 0:
            default_admin_user = os.environ.get("ADMIN_USERNAME", "admin")
            default_admin_pass = os.environ.get("ADMIN_PASSWORD", "Admin@123")
            admin_hash = generate_password_hash(default_admin_pass)
            if is_postgres():
                cur.execute(
                    "INSERT INTO admins (username, password_hash, created_at) VALUES (%s, %s, %s)",
                    (default_admin_user, admin_hash, now_iso)
                )
            else:
                cur.execute(
                    "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (default_admin_user, admin_hash, now_iso)
                )
            conn.commit()

        # Seed initial active rice mills for Mandapeta if none exist
        cur.execute("SELECT COUNT(*) FROM rice_mills")
        mill_count = cur.fetchone()[0]
        if mill_count == 0:
            initial_mills = [
                ("Sri Venkateswara Modern Rice Mill", "Alamuru Road, Mandapeta, East Godavari"),
                ("Sri Vijaya Durga Agro Industries", "Kakinada Road, Mandapeta, East Godavari"),
                ("Sri Satyanarayana Boiled & Raw Rice Mill", "Dwarapudi Road, Mandapeta, East Godavari"),
                ("Sri Laxmi Ganapathi Rice Industries", "Pedapudi Bypass, Mandapeta, East Godavari"),
                ("Srinivasa Modern Rice Mill", "Main Road, Mandapeta, East Godavari")
            ]
            for m_name, m_loc in initial_mills:
                if is_postgres():
                    cur.execute(
                        "INSERT INTO rice_mills (mill_name, location, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)",
                        (m_name, m_loc, True, now_iso, now_iso)
                    )
                else:
                    cur.execute(
                        "INSERT INTO rice_mills (mill_name, location, is_active, created_at, updated_at) VALUES (?, ?, 1, ?, ?)",
                        (m_name, m_loc, now_iso, now_iso)
                    )
            conn.commit()

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
