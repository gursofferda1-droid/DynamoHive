import time
import threading
from queue import Queue, Empty


class SignalQueue:
    """
    V2 CORE SIGNAL BUFFER
    - Backpressure control
    - Ordered processing
    - Safe buffering layer between event bus and workers
    """

    def __init__(self, maxsize=1000):
        self.queue = Queue(maxsize=maxsize)
        self._lock = threading.Lock()

        self.dropped = 0
        self.processed = 0

        self.running = False

    # -------------------------
    # PUSH SIGNAL
    # -------------------------
    def push(self, signal):
        try:
            self.queue.put_nowait({
                "signal": signal,
                "timestamp": time.time()
            })
        except Exception:
            # queue full → backpressure
            self.dropped += 1

    # -------------------------
    # POP SIGNAL
    # -------------------------
    def pop(self, timeout=1):
        try:
            item = self.queue.get(timeout=timeout)
            self.processed += 1
            return item["signal"]
        except Empty:
            return None

    # -------------------------
    # BATCH POP
    # -------------------------
    def pop_batch(self, size=10):
        batch = []

        for _ in range(size):
            item = self.pop(timeout=0.1)
            if item is None:
                break
            batch.append(item)

        return batch

    # -------------------------
    # STATS
    # -------------------------
    def stats(self):
        with self._lock:
            return {
                "size": self.queue.qsize(),
                "processed": self.processed,
                "dropped": self.dropped
            }

    # -------------------------
    # CLEAR
    # -------------------------
    def clear(self):
        with self._lock:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except Exception:
                    break
