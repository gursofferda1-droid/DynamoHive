import sqlite3
import os
import time
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "dynamohive.db")


# -------------------------
# INIT DB (SAFE)
# -------------------------
def init_db():
    os.makedirs(DB_DIR, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_created_at
            ON posts(created_at)
        """)

        conn.commit()


# -------------------------
# CONNECTION MANAGER
# -------------------------
@contextmanager
def get_connection():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()


# -------------------------
# SAVE POST
# -------------------------
def save_post(title, content):
    if not title or not content:
        return False

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO posts (title, content)
                VALUES (?, ?)
            """, (title, content))

            conn.commit()
            return True

    except Exception as e:
        print("[DB WRITE ERROR]", e)
        return False


# -------------------------
# GET POSTS
# -------------------------
def get_posts(limit=50):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, title, content, created_at
                FROM posts
                ORDER BY datetime(created_at) DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()

        posts = []

        for row in rows:
            post = dict(row)

            # safe timestamp
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
        print("[DB READ ERROR]", e)
        return []


# -------------------------
# HEALTH CHECK
# -------------------------
def db_health():
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except:
        return False
