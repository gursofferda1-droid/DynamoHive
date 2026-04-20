import time

from backend.logger import logger


class MemoryEngine:

    def __init__(self):
        self.store = {}
        self.max_age = 86400      # 24 saat
        self.max_items = 1000

    def _topic_key(self, signal):
        return str(
            signal.get("topic") or
            signal.get("title") or
            ""
        ).strip().lower()

    def _default(self):
        return {
            "history": [],
            "related_events": []
        }

    def _cleanup(self):
        now = time.time()

        expired = [
            key for key, value in self.store.items()
            if now - value.get("timestamp", now) > self.max_age
        ]

        for key in expired:
            self.store.pop(key, None)

        if len(self.store) > self.max_items:
            ordered = sorted(
                self.store.items(),
                key=lambda x: x[1].get("timestamp", 0)
            )

            overflow = len(self.store) - self.max_items

            for key, _ in ordered[:overflow]:
                self.store.pop(key, None)

    def load(self, signal):

        try:
            topic = self._topic_key(signal)

            if not topic:
                return self._default()

            item = self.store.get(topic)

            if not item:
                return self._default()

            return item.get("data", self._default())

        except Exception as e:
            logger.warning(f"[MEMORY LOAD ERROR] {e}")
            return self._default()

    def save(self, signal, data):

        try:
            topic = self._topic_key(signal)

            if not topic:
                return

            self.store[topic] = {
                "timestamp": time.time(),
                "data": data
            }

            self._cleanup()

        except Exception as e:
            logger.warning(f"[MEMORY SAVE ERROR] {e}")
