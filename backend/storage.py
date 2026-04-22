import sqlite3
import os
import time
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "dynamohive.db")


# -------------------------
# INIT DB (SAFE + STABLE)
# -------------------------
def init_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # performance + concurrency
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            hash TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# -------------------------
# CONNECTION
# -------------------------
def get_connection():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------
# HASH (IDEMPOTENCY CORE)
# -------------------------
def generate_hash(title, content):
    raw = f"{str(title).strip().lower()}::{str(content).strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()


# -------------------------
# SAVE POST (SAFE WRITE)
# -------------------------
def save_post(title, content):

    h = generate_hash(title, content)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # duplicate guard at DB level
            cursor.execute("""
                INSERT OR IGNORE INTO posts (title, content, hash)
                VALUES (?, ?, ?)
            """, (title, content, h))

            conn.commit()

            return True

    except Exception as e:
        print("DB WRITE ERROR:", e)
        return False


# -------------------------
# GET POSTS (STATE READ)
# -------------------------
def get_posts(limit=50):

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, title, content, created_at
                FROM posts
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()

        results = []

        for row in rows:
            item = dict(row)

            try:
                item["timestamp"] = time.mktime(
                    time.strptime(item["created_at"], "%Y-%m-%d %H:%M:%S")
                )
            except:
                item["timestamp"] = time.time()

            item["source"] = "internal"
            results.append(item)

        return results

    except Exception as e:
        print("DB READ ERROR:", e)
        return []
