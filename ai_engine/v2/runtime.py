import time
import threading


class Runtime:
    """
    V2 CORE RUNTIME CONTROLLER
    - System lifecycle manager
    - Coordinates EventBus + Queue + Workers + State
    - Heartbeat + cycle control
    """

    def __init__(self, state_store, event_bus, signal_queue, worker_pool):
        self.state = state_store
        self.bus = event_bus
        self.queue = signal_queue
        self.workers = worker_pool

        self.running = False
        self.thread = None

    # -------------------------
    # START SYSTEM
    # -------------------------
    def start(self):

        self.running = True
        self.state.set("running", True)

        self.workers.start()

        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

        print("[RUNTIME] STARTED")

    # -------------------------
    # MAIN LOOP (HEARTBEAT)
    # -------------------------
    def _loop(self):

        while self.running:

            try:
                cycle = self.state.next_cycle()

                # heartbeat event
                self.bus.emit("heartbeat", {
                    "cycle": cycle,
                    "timestamp": time.time()
                })

                # flush signals → workers
                batch = self.queue.pop_batch(20)

                for signal in batch:
                    self.workers.submit({
                        "handler": signal.get("handler"),
                        "data": signal
                    })

                time.sleep(1)

            except Exception as e:
                self.state.inc_metric("errors")
                print("[RUNTIME ERROR]", e)

    # -------------------------
    # STOP SYSTEM
    # -------------------------
    def stop(self):

        self.running = False
        self.state.set("running", False)

        self.workers.stop()

        print("[RUNTIME] STOPPED")

    # -------------------------
    # STATUS
    # -------------------------
    def status(self):

        return {
            "running": self.running,
            "cycle": self.state.get_cycle(),
            "metrics": self.state.get_metrics(),
            "queue_size": self.queue.stats(),
            "workers": self.workers.status()
        }
