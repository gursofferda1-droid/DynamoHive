from backend.events import detect_event_spikes
from backend.storage import get_posts
from backend.orchestrator import LAST_DATA


def get_system_metrics(orchestrator=None):

    posts = get_posts()
    spikes = detect_event_spikes()

    # -------------------------
    # ORCHESTRATOR SAFE READ
    # -------------------------
    cycle = getattr(orchestrator, "cycle", 0) if orchestrator else 0

    # -------------------------
    # SIGNAL INFO
    # -------------------------
    last_signal_count = len(LAST_DATA) if LAST_DATA else 0
    last_event_count = len(spikes) if spikes else 0

    # -------------------------
    # DOMINANCE (basit çıkarım)
    # -------------------------
    dominance_map = {}

    for p in posts[:30]:
        title = (p.get("title") or "unknown").lower()

        key = title[:40]
        dominance_map[key] = dominance_map.get(key, 0) + 1

    dominance = [
        {"topic": k, "dominance": v}
        for k, v in sorted(dominance_map.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    # -------------------------
    # ANOMALY (basit spike mapping)
    # -------------------------
    anomalies = []

    for s in spikes[:5]:
        anomalies.append({
            "type": s.get("type", "spike"),
            "topic": s.get("topic", "unknown")
        })

    # -------------------------
    # OUTPUT (FRONTEND UYUMLU)
    # -------------------------
    metrics = {
        "orchestrator": {
            "cycle_count": cycle,
            "last_signal_count": last_signal_count,
            "last_event_count": last_event_count,
            "dominance": dominance,
            "anomalies": anomalies
        },
        "status": "running"
    }

    return metrics
