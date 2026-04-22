import time
import threading
from collections import defaultdict
from queue import Queue


class EventBus:
    """
    V2 CORE EVENT BUS
    - Pub/Sub system
    - Decoupled architecture
    - Async-safe event dispatch
    """

    def __init__(self):
        self._lock = threading.Lock()

        # event_name -> [handlers]
        self.subscribers = defaultdict(list)

        # event queue
        self.queue = Queue()

        self.running = False

    # -------------------------
    # SUBSCRIBE
    # -------------------------
    def subscribe(self, event_name, handler):
        with self._lock:
            self.subscribers[event_name].append(handler)

    # -------------------------
    # PUBLISH
    # -------------------------
    def publish(self, event_name, data=None):
        self.queue.put({
            "event": event_name,
            "data": data,
            "timestamp": time.time()
        })

    # -------------------------
    # INTERNAL DISPATCH
    # -------------------------
    def _dispatch(self, event):
        name = event["event"]
        data = event["data"]

        handlers = []

        with self._lock:
            handlers = list(self.subscribers.get(name, []))

        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                print(f"[EVENT BUS ERROR] {name}: {e}")

    # -------------------------
    # RUN LOOP
    # -------------------------
    def start(self):
        self.running = True

        while self.running:
            try:
                event = self.queue.get(timeout=1)
                self._dispatch(event)
            except Exception:
                continue

    # -------------------------
    # STOP
    # -------------------------
    def stop(self):
        self.running = False

    # -------------------------
    # SAFE PUBLISH (SYNC)
    # -------------------------
    def emit(self, event_name, data=None):
        self.publish(event_name, data)
