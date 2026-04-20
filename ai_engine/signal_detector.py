from collections import defaultdict
import re

from backend.logger import logger


def normalize(text):
    try:
        text = str(text).lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    except Exception:
        return ""


def classify_topic(text):
    t = text.lower()

    if any(x in t for x in ["war", "attack", "missile", "conflict", "sanction"]):
        return "geopolitical"

    if any(x in t for x in ["ai", "chip", "robot", "automation", "openai"]):
        return "technology"

    if any(x in t for x in ["market", "economy", "ipo", "inflation", "recession"]):
        return "economic"

    if any(x in t for x in ["protest", "migration", "society", "election"]):
        return "social"

    return "general"


def compute_score(text, count):
    try:
        t = text.lower()

        base = min(0.3 + (count * 0.1), 0.6)
        bonus = 0.0

        strong_terms = [
            "war", "attack", "crisis", "collapse",
            "ai", "nuclear", "conflict", "sanction"
        ]

        if any(w in t for w in strong_terms):
            bonus += 0.25

        score = min(base + bonus, 1.0)

        return round(score, 3)

    except Exception:
        return 0.5


def detect_signals(analysis):

    try:
        if not isinstance(analysis, list) or not analysis:
            logger.info("[SIGNALS] detected=0")
            return []

        grouped = defaultdict(int)
        originals = {}

        for item in analysis:
            try:
                if not isinstance(item, dict):
                    continue

                raw = item.get("title") or item.get("text") or item.get("topic") or ""
                raw = str(raw).strip()

                if not raw:
                    continue

                normalized = normalize(raw)

                if not normalized:
                    continue

                key = " ".join(normalized.split()[:6])

                grouped[key] += 1

                if key not in originals:
                    originals[key] = raw[:120]

            except Exception:
                continue

        signals = []

        for key, count in grouped.items():
            topic = originals.get(key, key)

            score = compute_score(topic, count)
            category = classify_topic(topic)

            signals.append({
                "topic": topic,
                "title": topic,
                "score": score,
                "count": count,
                "category": category
            })

        if not signals:
            for item in analysis[:5]:
                raw = str(item.get("title") or item.get("text") or "").strip()

                if not raw:
                    continue

                signals.append({
                    "topic": raw[:120],
                    "title": raw[:120],
                    "score": 0.5,
                    "count": 1,
                    "category": "general"
                })

        if not signals:
            signals = [{
                "topic": "fallback signal",
                "title": "fallback signal",
                "score": 0.5,
                "count": 1,
                "category": "general"
            }]

        signals.sort(key=lambda x: x.get("score", 0), reverse=True)

        logger.info(f"[SIGNALS] detected={len(signals)}")

        return signals

    except Exception as e:
        logger.warning(f"[SIGNAL DETECTOR ERROR] {e}")

        return [{
            "topic": "fallback signal",
            "title": "fallback signal",
            "score": 0.5,
            "count": 1,
            "category": "general"
        }]
