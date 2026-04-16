import hashlib
from datetime import datetime


TEMPLATES = [
    "Recent developments in {topic} show significant global momentum.",
    "Experts highlight growing influence of {topic} across industries.",
    "New discussions around {topic} are shaping global debates.",
    "Analysts report increasing attention toward {topic} worldwide."
]


def _stable_index(topic, length):
    digest = hashlib.md5(topic.encode()).hexdigest()
    return int(digest, 16) % length


def build_title(topic):
    titles = [
        f"Global developments in {topic}",
        f"New signals emerging in {topic}",
        f"Trends shaping the future of {topic}",
        f"Why {topic} is gaining global attention"
    ]

    index = _stable_index(topic, len(titles))
    return titles[index]


def build_content(topic):
    return " ".join([t.format(topic=topic) for t in TEMPLATES])


def generate_content(event):
    if not event or not isinstance(event, dict):
        return None

    topic = str(event.get("topic", "technology")).strip().lower()

    if not topic:
        return None

    insight = event.get("insight", "")

    if insight == "recurring_topic":
        print("skipped repeated topic:", topic)
        return None

    title = build_title(topic)
    content = build_content(topic)

    post = {
        "title": title,
        "content": content,
        "topic": topic,
        "created_at": datetime.utcnow().isoformat()
    }

    print("content generated:", title)

    return post
