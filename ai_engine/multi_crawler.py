import feedparser
import hashlib
import time

from backend.storage import save_post


# -------------------------
# SOURCES
# -------------------------
RSS_SOURCES = [
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
]


# -------------------------
# CACHE SYSTEM
# -------------------------
CACHE = {}
CACHE_TTL = 300  # 5 min

SEEN = {}
DUP_TTL = 1800  # 30 min


# -------------------------
# HELPERS
# -------------------------
def _hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _is_duplicate(text: str) -> bool:
    h = _hash(text)
    now = time.time()

    if h in SEEN and (now - SEEN[h]) < DUP_TTL:
        return True

    SEEN[h] = now
    return False


def _get_feed(url: str):
    now = time.time()

    if url in CACHE:
        ts, data = CACHE[url]
        if now - ts < CACHE_TTL:
            return data

    try:
        feed = feedparser.parse(url, request_headers={
            "User-Agent": "Mozilla/5.0"
        })
    except:
        return None

    CACHE[url] = (now, feed)
    return feed


# -------------------------
# MAIN CRAWLER
# -------------------------
def crawl():

    results = []

    for url in RSS_SOURCES:

        feed = _get_feed(url)

        if not feed or not getattr(feed, "entries", None):
            continue

        print(f"[CRAWL] {url} entries:", len(feed.entries))

        for entry in feed.entries[:5]:

            try:
                title = (entry.get("title") or "").strip()
                summary = entry.get("summary") or entry.get("description") or ""

                if not title:
                    continue

                text = f"{title} {summary}"

                # duplicate filter
                if _is_duplicate(text):
                    continue

                item = {
                    "title": title,
                    "content": summary.strip() if summary else title,
                    "source": url,
                    "timestamp": time.time()
                }

                results.append(item)

                # DB write (fail-safe)
                try:
                    save_post(item["title"], item["content"])
                except Exception as e:
                    print("DB write error:", e)

                print("ADD:", title[:60])

            except Exception:
                continue

    print("crawler collected:", len(results))

    return results
    
