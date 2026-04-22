class ExecutionGraph:
    """
    V2 CORE EXECUTION LAYER
    - Forces deterministic pipeline
    - Binds signal → intelligence → decision → storage
    - Removes "loose module" behavior
    """

    def __init__(self, state, bus, queue, worker_pool, intelligence_engine, decision_engine, storage):
        self.state = state
        self.bus = bus
        self.queue = queue
        self.workers = worker_pool
        self.intelligence = intelligence_engine
        self.decision = decision_engine
        self.storage = storage

    # -------------------------
    # MAIN EXECUTION FLOW
    # -------------------------
    def execute(self, signal):

        try:
            self.bus.emit("execution_started", signal)

            # 1. INTELLIGENCE
            intel = self.intelligence.run([signal])

            if not intel:
                self.state.inc_metric("errors")
                return None

            item = intel[0]

            # 2. DECISION
            decision_list = self.decision.evaluate([item])

            if not decision_list:
                return None

            decision = decision_list[0].get("decision", {})

            if not decision.get("publish", False):
                self.bus.emit("skipped", item)
                return None

            # 3. GENERATION
            narrative = item.get("narrative", {})

            title = narrative.get("title", item.get("topic", "untitled"))
            content = narrative.get("content", "")

            # 4. STORAGE
            self.storage(title, content)

            # 5. METRICS
            self.state.inc_metric("generated_posts")

            self.bus.emit("execution_success", {
                "title": title
            })

            return True

        except Exception as e:
            self.state.inc_metric("errors")
            self.bus.emit("execution_error", str(e))
            return None
