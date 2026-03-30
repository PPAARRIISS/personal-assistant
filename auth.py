import sqlite3
import os
import bcrypt

AUTH_DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def get_conn():
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            name       TEXT NOT NULL,
            password   TEXT NOT NULL,
            onboarded  INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def register_user(username, name, password):
    username = username.strip().lower()
    if not username or not name or not password:
        return False, "All fields are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO users (username, name, password) VALUES (?, ?, ?)",
            (username, name.strip(), hashed)
        )
        conn.commit()
        conn.close()
        return True, None
    except sqlite3.IntegrityError:
        return False, "Username already taken. Please choose another."


def verify_login(username, password):
    username = username.strip().lower()
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if row and bcrypt.checkpw(password.encode(), row["password"].encode()):
        return True, row["name"], bool(row["onboarded"])
    return False, None, False


def mark_onboarded(username):
    conn = get_conn()
    conn.execute("UPDATE users SET onboarded=1 WHERE username=?", (username,))
    conn.commit()
    conn.close()


init_auth_db()
