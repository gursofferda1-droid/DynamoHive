import sqlite3
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "dynamohive.db")

_db_initialized = False


def init_db():
    global _db_initialized

    if _db_initialized:
        return

    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Performans ve kilitlenme iyileştirmeleri
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    _db_initialized = True


def get_connection():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def save_post(title, content):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO posts (title, content)
                VALUES (?, ?)
            """, (title, content))
            conn.commit()

    except Exception as e:
        print("DB write error:", e)


def get_posts(limit=50):
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
