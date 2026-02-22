import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta
import bisect

DB_PATH = Path("data/app.db")

def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _add_column_if_missing(cur, table: str, column: str, coldef: str):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r["name"] for r in cur.fetchall()]
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coldef}")

def _cost_for_level(lvl: int) -> int:
    if 1 <= lvl <= 10:
        return 1
    if 11 <= lvl <= 20:
        return 2
    if 21 <= lvl <= 40:
        return 3
    if 41 <= lvl <= 60:
        return 4
    if 61 <= lvl <= 80:
        return 5
    return 6

def _build_thresholds():
    thresholds = [-1] + [0] * 100
    total = 0
    thresholds[1] = 0
    for lvl in range(1, 100):
        total += _cost_for_level(lvl)
        thresholds[lvl + 1] = total
    return thresholds

TREE_THRESHOLDS = _build_thresholds()

def _level_from_total(total_entries: int):
    total_entries = max(0, int(total_entries))
    lvl = bisect.bisect_right(TREE_THRESHOLDS, total_entries) - 1
    if lvl < 1:
        lvl = 1
    if lvl > 100:
        lvl = 100

    prev_need = TREE_THRESHOLDS[lvl]
    next_need = TREE_THRESHOLDS[lvl + 1] if lvl < 100 else prev_need

    in_level = total_entries - prev_need
    need_for_next = max(0, next_need - prev_need)
    to_next = max(0, next_need - total_entries)

    stage = ((lvl - 1) // 10) + 1

    return {
        "level": lvl,
        "stage": stage,
        "prev_need": prev_need,
        "next_need": next_need,
        "in_level": in_level,
        "need_for_next": need_for_next,
        "to_next": to_next,
    }

def init_db():
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            mode TEXT DEFAULT NULL,
            created_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS diary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            day TEXT NOT NULL,
            score INTEGER,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS todo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'todo',
            created_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS sleep_settings (
            user_id TEXT PRIMARY KEY,
            bedtime TEXT,
            waketime TEXT,
            enabled INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT
        )
        """)

        _add_column_if_missing(cur, "sleep_settings", "waketime", "TEXT")
        _add_column_if_missing(cur, "sleep_settings", "updated_at", "TEXT")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS journal_state (
            user_id TEXT PRIMARY KEY,
            idx INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT
        )
        """)

        _add_column_if_missing(cur, "journal_state", "updated_at", "TEXT")

        conn.commit()

def upsert_user(user_id: str):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users(user_id, created_at) VALUES (?, ?)",
            (user_id, now)
        )
        conn.commit()

def set_mode(user_id: str, mode: str | None):
    with get_conn() as conn:
        conn.execute("UPDATE users SET mode=? WHERE user_id=?", (mode, user_id))
        conn.commit()

def get_mode(user_id: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT mode FROM users WHERE user_id=?", (user_id,)).fetchone()
        return row["mode"] if row else None

def add_diary(user_id: str, text: str, score: int | None):
    now = datetime.utcnow().isoformat()
    today = date.today().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO diary(user_id, day, score, text, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, today, score, text, now)
        )
        conn.commit()

def add_todo(user_id: str, title: str):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO todo(user_id, title, status, created_at) VALUES (?, ?, 'todo', ?)",
            (user_id, title, now)
        )
        conn.commit()

def list_todo(user_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, status FROM todo WHERE user_id=? ORDER BY id DESC LIMIT 20",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def mark_todo_done(user_id: str, todo_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE todo SET status='done' WHERE user_id=? AND id=?",
            (user_id, todo_id)
        )
        conn.commit()

def clear_done_todos(user_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM todo WHERE user_id=? AND status='done'", (user_id,))
        conn.commit()

def set_sleep(user_id: str, bedtime: str | None, waketime: str | None, enabled: int):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sleep_settings(user_id, bedtime, waketime, enabled, updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET bedtime=excluded.bedtime, waketime=excluded.waketime, enabled=excluded.enabled, updated_at=excluded.updated_at",
            (user_id, bedtime, waketime, int(enabled), now)
        )
        conn.commit()

def get_sleep_setting(user_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT bedtime, waketime, enabled FROM sleep_settings WHERE user_id=?",
            (user_id,)
        ).fetchone()
        if not row:
            return {"bedtime": None, "waketime": None, "enabled": 0}
        return {"bedtime": row["bedtime"], "waketime": row["waketime"], "enabled": int(row["enabled"])}

def get_sleep_settings():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id, bedtime, waketime, enabled FROM sleep_settings WHERE enabled=1"
        ).fetchall()
        return [dict(r) for r in rows]

def get_diary_stats(user_id: str):
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) as c FROM diary WHERE user_id=?",
            (user_id,)
        ).fetchone()["c"]

        today = date.today().isoformat()
        row_today = conn.execute(
            "SELECT COUNT(*) as c FROM diary WHERE user_id=? AND day=?",
            (user_id, today)
        ).fetchone()
        did_today = 1 if row_today["c"] > 0 else 0

        streak = 0
        d = date.today()
        while True:
            ds = d.isoformat()
            r = conn.execute(
                "SELECT COUNT(*) as c FROM diary WHERE user_id=? AND day=?",
                (user_id, ds)
            ).fetchone()
            if r["c"] > 0:
                streak += 1
                d = d - timedelta(days=1)
            else:
                break

        lv = _level_from_total(total)
        return {
            "total": int(total),
            "streak": int(streak),
            "did_today": int(did_today),
            "level": lv["level"],
            "stage": lv["stage"],
            "in_level": lv["in_level"],
            "need_for_next": lv["need_for_next"],
            "to_next": lv["to_next"],
            "next_need": lv["next_need"],
        }

def get_journal_idx(user_id: str) -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT idx FROM journal_state WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            now = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT INTO journal_state(user_id, idx, updated_at) VALUES (?, 0, ?)",
                (user_id, now)
            )
            conn.commit()
            return 0
        return int(row["idx"])

def set_journal_idx(user_id: str, idx: int):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO journal_state(user_id, idx, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET idx=excluded.idx, updated_at=excluded.updated_at",
            (user_id, int(idx), now)
        )
        conn.commit()