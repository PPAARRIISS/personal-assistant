import sqlite3
import os
from datetime import date, datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "productivity.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            pillar_id   INTEGER NOT NULL,
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
            pillar_id   INTEGER NOT NULL,
            log_date    TEXT NOT NULL,
            minutes     INTEGER NOT NULL,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()


# ── Tasks ────────────────────────────────────────────────────────────────────

def add_task(title, pillar_id, task_date, est_minutes=30, notes=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO tasks (title, pillar_id, task_date, est_minutes, notes) VALUES (?,?,?,?,?)",
        (title, pillar_id, str(task_date), est_minutes, notes)
    )
    conn.commit()
    conn.close()


def get_tasks_for_date(task_date):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE task_date = ? ORDER BY pillar_id, id",
        (str(task_date),)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tasks_for_week(week_start):
    from datetime import timedelta
    week_end = week_start + timedelta(days=6)
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE task_date BETWEEN ? AND ? ORDER BY task_date, pillar_id",
        (str(week_start), str(week_end))
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
    conn.execute(
        "UPDATE tasks SET is_completed=0, completed_at=NULL WHERE id=?",
        (task_id,)
    )
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_conn()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


# ── Time logs ─────────────────────────────────────────────────────────────────

def log_time(pillar_id, log_date, minutes, description=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO time_logs (pillar_id, log_date, minutes, description) VALUES (?,?,?,?)",
        (pillar_id, str(log_date), minutes, description)
    )
    conn.commit()
    conn.close()


def get_time_for_week(week_start):
    from datetime import timedelta
    week_end = week_start + timedelta(days=6)
    conn = get_conn()
    rows = conn.execute(
        """SELECT pillar_id, SUM(minutes) as total_minutes
           FROM time_logs WHERE log_date BETWEEN ? AND ?
           GROUP BY pillar_id""",
        (str(week_start), str(week_end))
    ).fetchall()
    conn.close()
    return {r["pillar_id"]: r["total_minutes"] for r in rows}


def get_time_for_date(log_date):
    conn = get_conn()
    rows = conn.execute(
        """SELECT pillar_id, SUM(minutes) as total_minutes
           FROM time_logs WHERE log_date = ?
           GROUP BY pillar_id""",
        (str(log_date),)
    ).fetchall()
    conn.close()
    return {r["pillar_id"]: r["total_minutes"] for r in rows}


def get_daily_breakdown_for_week(week_start):
    from datetime import timedelta
    week_end = week_start + timedelta(days=6)
    conn = get_conn()
    rows = conn.execute(
        """SELECT log_date, pillar_id, SUM(minutes) as total_minutes
           FROM time_logs WHERE log_date BETWEEN ? AND ?
           GROUP BY log_date, pillar_id
           ORDER BY log_date""",
        (str(week_start), str(week_end))
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Weekly stats helper ───────────────────────────────────────────────────────

def get_week_completion_stats(week_start):
    from datetime import timedelta
    week_end = week_start + timedelta(days=6)
    conn = get_conn()
    rows = conn.execute(
        """SELECT pillar_id,
                  COUNT(*) as total,
                  SUM(is_completed) as completed,
                  SUM(CASE WHEN is_completed=1 THEN act_minutes ELSE 0 END) as act_minutes,
                  SUM(est_minutes) as est_minutes
           FROM tasks WHERE task_date BETWEEN ? AND ?
           GROUP BY pillar_id""",
        (str(week_start), str(week_end))
    ).fetchall()
    conn.close()
    return {r["pillar_id"]: dict(r) for r in rows}


# Initialise on import
init_db()
