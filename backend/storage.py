import sqlite3
import os
import time
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "dynamohive.db")


# -------------------------
# INIT
# -------------------------
def init_db():

    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # POSTS (çıktılar)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # FEEDBACK (platform öğrenme katmanı)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_title TEXT,
            signal_topic TEXT,
            engagement_score REAL DEFAULT 0,
            outcome TEXT,
            raw_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # STATE MEMORY (platform hafızası)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS state_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# -------------------------
# CONNECTION
# -------------------------
def get_connection():
    init_db()
    return sqlite3.connect(DB_PATH)


# -------------------------
# POSTS
# -------------------------
def save_post(title, content, signal_topic=None):

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO posts (title, content)
            VALUES (?, ?)
        """, (title, content))

        conn.commit()
        conn.close()

        # 🔥 AUTO FEEDBACK INIT (platform davranışı)
        if signal_topic:
            store_feedback(
                post_title=title,
                signal_topic=signal_topic,
                engagement_score=0.0,
                outcome="generated"
            )

    except Exception as e:
        print("DB write error:", e)


def get_posts():

    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, content, created_at
            FROM posts
            ORDER BY created_at DESC
            LIMIT 50
        """)

        rows = cursor.fetchall()
        conn.close()

        posts = []

        for row in rows:
            post = dict(row)

            try:
                post["timestamp"] = time.mktime(
                    time.strptime(post["created_at"], "%Y-%m-%d %H:%M:%S")
                )
            except:
                post["timestamp"] = time.time()

            posts.append(post)

        return posts

    except Exception as e:
        print("DB read error:", e)
        return []


# -------------------------
# FEEDBACK SYSTEM (KRİTİK EKLENDİ)
# -------------------------
def store_feedback(post_title, signal_topic, engagement_score=0.0, outcome="unknown", raw=None):

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO feedback (
                post_title,
                signal_topic,
                engagement_score,
                outcome,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            post_title,
            signal_topic,
            engagement_score,
            outcome,
            json.dumps(raw or {})
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        print("FEEDBACK write error:", e)


def get_feedback(limit=100):

    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM feedback
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(r) for r in rows]

    except Exception as e:
        print("FEEDBACK read error:", e)
        return []


# -------------------------
# STATE MEMORY (platform hafızası)
# -------------------------
def set_state(key, value):

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO state_memory (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                updated_at=CURRENT_TIMESTAMP
        """, (key, json.dumps(value)))

        conn.commit()
        conn.close()

    except Exception as e:
        print("STATE write error:", e)


def get_state(key):

    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT value FROM state_memory
            WHERE key=?
        """, (key,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return json.loads(row["value"])

    except Exception as e:
        print("STATE read error:", e)
        return None
