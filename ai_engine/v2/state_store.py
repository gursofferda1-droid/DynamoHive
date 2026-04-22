import time
import threading


class StateStore:
    """
    V2 CORE STATE LAYER
    - Cycle state
    - Runtime memory
    - Shared system context
    - Thread-safe global store
    """

    def __init__(self):
        self._lock = threading.Lock()

        self.state = {
            "cycle": 0,
            "running": False,
            "last_run": None,
            "metrics": {
                "processed_signals": 0,
                "generated_posts": 0,
                "crisis_hits": 0,
                "errors": 0
            },
            "cache": {},
            "events": [],
            "runtime_flags": {}
        }

    # -------------------------
    # BASIC GET / SET
    # -------------------------
    def get(self, key, default=None):
        with self._lock:
            return self.state.get(key, default)

    def set(self, key, value):
        with self._lock:
            self.state[key] = value

    # -------------------------
    # CYCLE CONTROL
    # -------------------------
    def next_cycle(self):
        with self._lock:
            self.state["cycle"] += 1
            self.state["last_run"] = time.time()
            return self.state["cycle"]

    def get_cycle(self):
        with self._lock:
            return self.state["cycle"]

    # -------------------------
    # METRICS
    # -------------------------
    def inc_metric(self, key, value=1):
        with self._lock:
            if key in self.state["metrics"]:
                self.state["metrics"][key] += value
            else:
                self.state["metrics"][key] = value

    def get_metrics(self):
        with self._lock:
            return dict(self.state["metrics"])

    # -------------------------
    # CACHE
    # -------------------------
    def cache_set(self, key, value):
        with self._lock:
            self.state["cache"][key] = {
                "value": value,
                "timestamp": time.time()
            }

    def cache_get(self, key, ttl=None):
        with self._lock:
            item = self.state["cache"].get(key)
            if not item:
                return None

            if ttl and (time.time() - item["timestamp"] > ttl):
                return None

            return item["value"]

    # -------------------------
    # EVENTS LOG
    # -------------------------
    def push_event(self, event):
        with self._lock:
            self.state["events"].append({
                "event": event,
                "timestamp": time.time()
            })

            # memory limit
            if len(self.state["events"]) > 1000:
                self.state["events"] = self.state["events"][-500:]
