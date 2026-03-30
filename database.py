import sqlite3
import os
from datetime import date, datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "productivity.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _has_column(c, table, column):
    c.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in c.fetchall())


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Drop and recreate tasks/time_logs if they have wrong schema
    for table in ["tasks", "time_logs"]:
        c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if c.fetchone() and not _has_column(c, table, "username"):
            c.execute(f"DROP TABLE {table}")

    c.execute("""
        CREATE TABLE IF NOT EXISTS pillars (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT NOT NULL,
            name            TEXT NOT NULL,
            icon            TEXT DEFAULT '📌',
            color           TEXT DEFAULT '#0078D4',
            bg              TEXT DEFAULT '#EBF3FB',
            daily_budget    INTEGER DEFAULT NULL,
            weekly_budget   INTEGER DEFAULT NULL,
            sort_order      INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL,
            pillar_id   INTEGER NOT NULL,
            title       TEXT NOT NULL,
            task_date   TEXT NOT NULL,
            est_minutes INTEGER DEFAULT 30,
            act_minutes INTEGER DEFAULT 0,
            is_completed INTEGER DEFAULT 0,
            completed_at TEXT,
            notes       TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS time_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL,
            pillar_id   INTEGER NOT NULL,
            log_date    TEXT NOT NULL,
            minutes     INTEGER NOT NULL,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # Migrations: add missing columns to existing tables
    for col, definition in [
        ("username", "TEXT NOT NULL DEFAULT 'default'"),
    ]:
        for table in ["tasks", "time_logs"]:
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
            except Exception:
                pass

    conn.commit()
    conn.close()


# ── Pillars ───────────────────────────────────────────────────────────────────

def get_pillars(username):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM pillars WHERE username=? ORDER BY sort_order, id",
        (username,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_pillar(username, name, icon, color, bg, daily_budget, weekly_budget):
    conn = get_conn()
    conn.execute(
        """INSERT INTO pillars (username, name, icon, color, bg, daily_budget, weekly_budget)
           VALUES (?,?,?,?,?,?,?)""",
        (username, name, icon, color, bg,
         daily_budget if daily_budget else None,
         weekly_budget if weekly_budget else None)
    )
    conn.commit()
    conn.close()


def update_pillar(pillar_id, name, icon, color, bg, daily_budget, weekly_budget):
    conn = get_conn()
    conn.execute(
        """UPDATE pillars SET name=?, icon=?, color=?, bg=?, daily_budget=?, weekly_budget=?
           WHERE id=?""",
        (name, icon, color, bg,
         daily_budget if daily_budget else None,
         weekly_budget if weekly_budget else None,
         pillar_id)
    )
    conn.commit()
    conn.close()


def delete_pillar(pillar_id):
    conn = get_conn()
    conn.execute("DELETE FROM pillars WHERE id=?", (pillar_id,))
    conn.execute("DELETE FROM tasks WHERE pillar_id=?", (pillar_id,))
    conn.execute("DELETE FROM time_logs WHERE pillar_id=?", (pillar_id,))
    conn.commit()
    conn.close()


def seed_pillars(username, pillars):
    """Seed a list of pillar dicts for a new user."""
    conn = get_conn()
    for i, p in enumerate(pillars):
        conn.execute(
            """INSERT INTO pillars (username, name, icon, color, bg, daily_budget, weekly_budget, sort_order)
               VALUES (?,?,?,?,?,?,?,?)""",
            (username, p["name"], p["icon"], p["color"], p["bg"],
             p.get("daily_budget"), p.get("weekly_budget"), i)
        )
    conn.commit()
    conn.close()


# ── Tasks ─────────────────────────────────────────────────────────────────────

def add_task(title, pillar_id, task_date, est_minutes=30, notes="", username="default"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO tasks (username, title, pillar_id, task_date, est_minutes, notes) VALUES (?,?,?,?,?,?)",
        (username, title, pillar_id, str(task_date), est_minutes, notes)
    )
    conn.commit()
    conn.close()


def get_tasks_for_date(task_date, username="default"):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE task_date=? AND username=? ORDER BY pillar_id, id",
        (str(task_date), username)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tasks_for_week(week_start, username="default"):
    from datetime import timedelta
    week_end = week_start + timedelta(days=6)
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE task_date BETWEEN ? AND ? AND username=? ORDER BY task_date, pillar_id",
        (str(week_start), str(week_end), username)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def complete_task(task_id, act_minutes=None):
    conn = get_conn()
    now = datetime.now().isoformat()
    if act_minutes is not None:
        conn.execute(
            "UPDATE tasks SET is_completed=1, completed_at=?, act_minutes=? WHERE id=?",
            (now, act_minutes, task_id)
        )
    else:
        conn.execute(
            "UPDATE tasks SET is_completed=1, completed_at=? WHERE id=?",
            (now, task_id)
        )
    conn.commit()
    conn.close()


def uncomplete_task(task_id):
    conn = get_conn()
    conn.execute("UPDATE tasks SET is_completed=0, completed_at=NULL WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_conn()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


# ── Time logs ─────────────────────────────────────────────────────────────────

def log_time(pillar_id, log_date, minutes, description="", username="default"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO time_logs (username, pillar_id, log_date, minutes, description) VALUES (?,?,?,?,?)",
        (username, pillar_id, str(log_date), minutes, description)
    )
    conn.commit()
    conn.close()


def get_time_for_week(week_start, username="default"):
    from datetime import timedelta
    week_end = week_start + timedelta(days=6)
    conn = get_conn()
    rows = conn.execute(
        """SELECT pillar_id, SUM(minutes) as total_minutes
           FROM time_logs WHERE log_date BETWEEN ? AND ? AND username=?
           GROUP BY pillar_id""",
        (str(week_start), str(week_end), username)
    ).fetchall()
    conn.close()
    return {r["pillar_id"]: r["total_minutes"] for r in rows}


def get_time_for_date(log_date, username="default"):
    conn = get_conn()
    rows = conn.execute(
        """SELECT pillar_id, SUM(minutes) as total_minutes
           FROM time_logs WHERE log_date=? AND username=?
           GROUP BY pillar_id""",
        (str(log_date), username)
    ).fetchall()
    conn.close()
    return {r["pillar_id"]: r["total_minutes"] for r in rows}


def get_daily_breakdown_for_week(week_start, username="default"):
    from datetime import timedelta
    week_end = week_start + timedelta(days=6)
    conn = get_conn()
    rows = conn.execute(
        """SELECT log_date, pillar_id, SUM(minutes) as total_minutes
           FROM time_logs WHERE log_date BETWEEN ? AND ? AND username=?
           GROUP BY log_date, pillar_id ORDER BY log_date""",
        (str(week_start), str(week_end), username)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_week_completion_stats(week_start, username="default"):
    from datetime import timedelta
    week_end = week_start + timedelta(days=6)
    conn = get_conn()
    rows = conn.execute(
        """SELECT pillar_id, COUNT(*) as total,
                  SUM(is_completed) as completed,
                  SUM(CASE WHEN is_completed=1 THEN act_minutes ELSE 0 END) as act_minutes,
                  SUM(est_minutes) as est_minutes
           FROM tasks WHERE task_date BETWEEN ? AND ? AND username=?
           GROUP BY pillar_id""",
        (str(week_start), str(week_end), username)
    ).fetchall()
    conn.close()
    return {r["pillar_id"]: dict(r) for r in rows}


init_db()
