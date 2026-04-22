import time
import threading
from queue import Queue


class WorkerPool:
    """
    V2 CORE WORKER POOL
    - Parallel execution layer
    - Processes signals from SignalQueue
    - Stateless workers
    """

    def __init__(self, worker_count=4):
        self.worker_count = worker_count
        self.threads = []

        self.task_queue = Queue()

        self.running = False

        self.stats = {
            "processed": 0,
            "failed": 0
        }

    # -------------------------
    # SUBMIT TASK
    # -------------------------
    def submit(self, task):
        self.task_queue.put(task)

    # -------------------------
    # WORKER LOGIC
    # -------------------------
    def _worker(self, worker_id):
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)

                self._execute(task, worker_id)

                self.stats["processed"] += 1

            except Exception:
                continue

    # -------------------------
    # EXECUTION CORE
    # -------------------------
    def _execute(self, task, worker_id):
        try:
            handler = task.get("handler")
            data = task.get("data")

            if handler:
                handler(data)

        except Exception as e:
            self.stats["failed"] += 1
            print(f"[WORKER {worker_id} ERROR]", e)

    # -------------------------
    # START POOL
    # -------------------------
    def start(self):
        self.running = True

        for i in range(self.worker_count):
            t = threading.Thread(target=self._worker, args=(i,), daemon=True)
            self.threads.append(t)
            t.start()

    # -------------------------
    # STOP POOL
    # -------------------------
    def stop(self):
        self.running = False

    # -------------------------
    # STATUS
    # -------------------------
    def status(self):
        return {
            "running": self.running,
            "workers": self.worker_count,
            "stats": self.stats
        }
