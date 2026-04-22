import sqlite3
import os
import time
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "dynamohive.db")


# -------------------------
# DB INIT
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

        conn.commit()


# -------------------------
# CONNECTION MANAGER
# -------------------------
@contextmanager
def get_connection():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# -------------------------
# SAVE POST
# -------------------------
def save_post(title, content):

    if not title or not content:
        return

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO posts (title, content)
                VALUES (?, ?)
            """, (title, content))

            conn.commit()

    except Exception as e:
        print("[DB WRITE ERROR]", e)


# -------------------------
# GET POSTS
# -------------------------
def get_posts(limit=50):

    posts = []

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, title, content, created_at
                FROM posts
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()

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

    except Exception as e:
        print("[DB READ ERROR]", e)

    return posts
