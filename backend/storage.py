import sqlite3
import hashlib

DB_PATH = "dynamohive.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def build_post_hash(title, content):
    raw = f"{title}|{content[:300]}"
    return hashlib.md5(raw.lower().strip().encode()).hexdigest()


def save_post(title, content):
    if not title:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            post_hash TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    post_hash = build_post_hash(title, content or "")

    try:
        cursor.execute("""
            INSERT INTO posts (title, content, post_hash)
            VALUES (?, ?, ?)
        """, (title, content, post_hash))

        conn.commit()
        conn.close()
        return True

    except sqlite3.IntegrityError:
        conn.close()
        return False

    except Exception:
        conn.close()
        return False
