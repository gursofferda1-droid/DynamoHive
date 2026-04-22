import sqlite3
import os
import time
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "dynamohive.db")


# -------------------------
# INIT DB (FULL PLATFORM STORAGE)
# -------------------------
def init_db():

    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ---------------- POSTS ----------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            decision_id TEXT,
            signal_id TEXT,
            topic TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---------------- SIGNALS ----------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            score REAL,
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---------------- DECISIONS ----------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            publish INTEGER,
            priority REAL,
            meta TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---------------- INTELLIGENCE ----------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intelligence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            narrative TEXT,
            reasoning TEXT,
            decision_ref TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_connection():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------
# POSTS (GENERATION OUTPUT)
# -------------------------
def save_post(title, content, decision_id=None, signal_id=None, topic=None):

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO posts (title, content, decision_id, signal_id, topic)
            VALUES (?, ?, ?, ?, ?)
        """, (title, content, decision_id, signal_id, topic))

        conn.commit()
        conn.close()

    except Exception as e:
        print("DB write error (post):", e)


# -------------------------
# SIGNAL STORAGE
# -------------------------
def save_signal(topic, score, raw_data):

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO signals (topic, score, raw_data)
            VALUES (?, ?, ?)
        """, (
            topic,
            float(score),
            json.dumps(raw_data)
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        print("DB write error (signal):", e)


# -------------------------
# DECISION STORAGE
# -------------------------
def save_decision(topic, decision):

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO decisions (topic, publish, priority, meta)
            VALUES (?, ?, ?, ?)
        """, (
            topic,
            1 if decision.get("publish") else 0,
            decision.get("priority", 0),
            json.dumps(decision)
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        print("DB write error (decision):", e)


# -------------------------
# INTELLIGENCE STORAGE
# -------------------------
def save_intelligence(topic, narrative, reasoning, decision_ref=None):

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO intelligence (topic, narrative, reasoning, decision_ref)
            VALUES (?, ?, ?, ?)
        """, (
            topic,
            json.dumps(narrative),
            json.dumps(reasoning),
            decision_ref
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        print("DB write error (intelligence):", e)


# -------------------------
# POSTS FETCH
# -------------------------
def get_posts():

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM posts
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

            post["keywords"] = []
            post["source"] = "internal"

            posts.append(post)

        return posts

    except Exception as e:
        print("DB read error:", e)
        return []
