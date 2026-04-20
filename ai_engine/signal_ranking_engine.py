import re
from difflib import SequenceMatcher

from backend.logger import logger


def normalize(text):
    try:
        text = str(text).lower()
        text = re.sub(r"[^a-z0-9 ]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception:
        return ""


def similar(a, b):
    try:
        if not a or not b:
            return False

        if a == b:
            return True

        return SequenceMatcher(None, a, b).ratio() > 0.78

    except Exception:
        return False


def merge_ranked_signals(signals):

    try:
        if not isinstance(signals, list):
            return []

        ranked = sorted(
            signals,
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        merged = []

        for s in ranked:

            if not isinstance(s, dict):
                continue

            topic_raw = s.get("topic") or s.get("text") or ""
            topic = normalize(topic_raw)

            if not topic:
                continue

            found = False

            for existing in merged:

                existing_topic = normalize(
                    existing.get("topic") or existing.get("text") or ""
                )

                if similar(topic, existing_topic):

                    old_score = float(existing.get("score", 0.5))
                    new_score = float(s.get("score", 0.5))

                    # kontrollü score merge
                    existing["score"] = round(
                        min((old_score + new_score) / 2 + 0.05, 1.0),
                        3
                    )

                    existing["count"] = existing.get("count", 1) + 1

                    if len(str(topic_raw)) > len(str(existing.get("topic", ""))):
                        existing["topic"] = topic_raw
                        existing["title"] = topic_raw

                    if not existing.get("category") and s.get("category"):
                        existing["category"] = s.get("category")

                    found = True
                    break

            if not found:
                merged.append({
                    **s,
                    "count": s.get("count", 1)
                })

        merged.sort(
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        logger.info(f"[RANKING] merged={len(merged)}")

        return merged

    except Exception as e:
        logger.warning(f"[RANKING ERROR] {e}")
        return signals if isinstance(signals, list) else []
