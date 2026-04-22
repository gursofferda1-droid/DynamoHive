import sqlite3
import os
import time
import json


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "events.db")


# -------------------------
# INIT EVENT DB
# -------------------------
def init_event_db():
    os.makedirs(DB_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            payload TEXT,
            created_at REAL
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_type
        ON events(type)
    """)

    conn.commit()
    conn.close()


# -------------------------
# WRITE EVENT
# -------------------------
def write_event(event_type: str, payload: dict):

    try:
        init_event_db()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO events (type, payload, created_at)
            VALUES (?, ?, ?)
        """, (
            event_type,
            json.dumps(payload, ensure_ascii=False),
            time.time()
        ))

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        print("[EVENT WRITE ERROR]", e)
        return False


# -------------------------
# READ EVENTS
# -------------------------
def get_events(event_type=None, limit=100):

    try:
        init_event_db()

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if event_type:
            cursor.execute("""
                SELECT * FROM events
                WHERE type = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (event_type, limit))
        else:
            cursor.execute("""
                SELECT * FROM events
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        events = []

        for r in rows:
            events.append({
                "id": r["id"],
                "type": r["type"],
                "payload": json.loads(r["payload"]),
                "created_at": r["created_at"]
            })

        return events

    except Exception as e:
        print("[EVENT READ ERROR]", e)
        return []


# -------------------------
# LOG HELPERS
# -------------------------
def log_signal(signal):
    return write_event("signal", signal)


def log_decision(decision):
    return write_event("decision", decision)


def log_generation(post):
    return write_event("generation", post)
