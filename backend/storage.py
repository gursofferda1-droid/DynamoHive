import sqlite3
import os
import time
import hashlib

from backend.logger import logger


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "dynamohive.db")


def init_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            title TEXT,
            content TEXT,
            priority REAL DEFAULT 0,
            source TEXT DEFAULT 'internal',
            content_hash TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_connection():
    init_db()
    return sqlite3.connect(DB_PATH)


def build_hash(title, content):
    raw = f"{title}|{content}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def save_post(title, content, topic=None, priority=0, source="internal"):

    try:
        conn = get_connection()
        cursor = conn.cursor()

        content_hash = build_hash(title, content)

        cursor.execute("""
            INSERT OR IGNORE INTO posts
            (topic, title, content, priority, source, content_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            topic or title,
            title,
            content,
            float(priority),
            source,
            content_hash
        ))

        conn.commit()
        conn.close()

        logger.info(f"[DB] saved: {title[:60]}")

    except Exception as e:
        logger.warning(f"[DB WRITE ERROR] {e}")


def get_posts(limit=50):

    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                topic,
                title,
                content,
                priority,
                source,
                created_at
            FROM posts
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        posts = []

        for row in rows:
            post = dict(row)

            try:
                post["timestamp"] = time.mktime(
                    time.strptime(
                        post["created_at"],
                        "%Y-%m-%d %H:%M:%S"
                    )
                )
            except Exception:
                post["timestamp"] = time.time()

            post["keywords"] = []

            posts.append(post)

        logger.info(f"[DB] loaded posts={len(posts)}")

        return posts

    except Exception as e:
        logger.warning(f"[DB READ ERROR] {e}")
        return []
