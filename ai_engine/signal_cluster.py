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


def simple_similarity(a, b):
    try:
        a_words = set(a.split())
        b_words = set(b.split())

        if not a_words or not b_words:
            return 0

        return len(a_words & b_words) / max(len(a_words), len(b_words))
    except Exception:
        return 0


def group_similar(signals, threshold=0.5):
    clusters = []
    used = set()

    for i, s1 in enumerate(signals):
        if i in used:
            continue

        cluster = [s1]
        used.add(i)

        t1 = normalize(s1.get("topic") or s1.get("title") or "")

        for j, s2 in enumerate(signals):
            if j in used:
                continue

            t2 = normalize(s2.get("topic") or s2.get("title") or "")

            sim = simple_similarity(t1, t2)

            if sim >= threshold:
                cluster.append(s2)
                used.add(j)

        clusters.append(cluster)

    return clusters


def merge_cluster(cluster):
    best = max(cluster, key=lambda x: x.get("score", 0))

    avg_score = sum(
        float(x.get("score", 0.5)) for x in cluster
    ) / max(len(cluster), 1)

    boosted_score = min(avg_score + (len(cluster) * 0.03), 1.0)

    return {
        "topic": best.get("topic") or best.get("title"),
        "title": best.get("title") or best.get("topic"),
        "content": best.get("content", ""),
        "score": round(boosted_score, 3),
        "count": sum(x.get("count", 1) for x in cluster),
        "cluster_size": len(cluster),
        "category": best.get("category", "general"),
        "sources": [x.get("source") for x in cluster if x.get("source")]
    }


def cluster_signals(signals):
    try:
        if not isinstance(signals, list) or not signals:
            return []

        grouped = group_similar(signals)
        merged = [merge_cluster(c) for c in grouped]

        merged.sort(
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        logger.info(f"[CLUSTER] clusters={len(merged)}")

        return merged

    except Exception as e:
        logger.warning(f"[CLUSTER ERROR] {e}")
        return signals if isinstance(signals, list) else []
