from backend.events import detect_event_spikes
from backend.storage import get_posts


SYSTEM_METRICS = {
    "cycle_count": 0,
    "last_signal_count": 0,
    "generated_count": 0,
    "skipped_count": 0,
    "last_event_count": 0,
    "dominance": [],
    "anomalies": [],
    "status": "running"
}


def update_metrics(data):
    try:
        if not isinstance(data, dict):
            return

        for key, value in data.items():
            SYSTEM_METRICS[key] = value

    except Exception as e:
        print("METRICS UPDATE ERROR:", e)


def get_system_metrics():
    try:
        posts = get_posts()
        spikes = detect_event_spikes()

        return {
            "orchestrator": {
                **SYSTEM_METRICS,
                "total_posts": len(posts),
                "latest_post": posts[0]["title"] if posts else None,
                "event_spikes": spikes[:5]
            }
        }

    except Exception as e:
        print("METRICS READ ERROR:", e)

        return {
            "orchestrator": SYSTEM_METRICS
        }
