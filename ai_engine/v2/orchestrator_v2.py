import time

from ai_engine.multi_crawler import crawl
from ai_engine.data_pipeline import process_data
from ai_engine.signal_detector import detect_signals
from ai_engine.signal_ranking_engine import merge_ranked_signals
from ai_engine.signal_cluster import cluster_signals
from ai_engine.global_crisis_radar import detect_crisis_signals

from backend.storage import save_post


class OrchestratorV2:
    """
    V2 ORCHESTRATOR (LIGHTWEIGHT)
    - No heavy logic
    - Only builds signals and pushes into runtime pipeline
    """

    def __init__(self, runtime, signal_queue, event_bus, state_store):
        self.runtime = runtime
        self.queue = signal_queue
        self.bus = event_bus
        self.state = state_store

        self.last_cache = []

    # -------------------------
    # MAIN CYCLE
    # -------------------------
    def run_cycle(self):

        start = time.time()

        try:
            cycle = self.state.next_cycle()

            self.bus.emit("cycle_started", {"cycle": cycle})

            # -------------------------
            # 1. DATA INGESTION
            # -------------------------
            raw = crawl()

            if not raw:
                raw = self.last_cache or [{"title": "fallback"}]

            raw = process_data(raw)

            self.last_cache = raw[:100]

            # -------------------------
            # 2. SIGNAL PIPELINE
            # -------------------------
            signals = detect_signals(raw)
            signals = merge_ranked_signals(signals)
            signals = cluster_signals(signals)

            crisis = detect_crisis_signals(raw)

            crisis_map = {
                str(c.get("title", "")).lower(): c
                for c in crisis
            }

            # -------------------------
            # 3. ENRICHMENT
            # -------------------------
            enriched = []

            for s in signals:

                topic = str(s.get("topic", "")).lower()

                if topic in crisis_map:
                    c = crisis_map[topic]
                    s["urgency"] = c.get("urgency", "high")
                    s["score"] = min(s.get("score", 0.5) + 0.3, 1.0)

                enriched.append(s)

            # -------------------------
            # 4. PUSH INTO V2 PIPELINE
            # -------------------------
            for signal in enriched:

                self.queue.push({
                    "signal": signal,
                    "handler": self._forward_to_runtime
                })

            self.bus.emit("signals_dispatched", {
                "count": len(enriched)
            })

            return len(enriched)

        except Exception as e:
            self.state.inc_metric("errors")
            print("[ORCHESTRATOR V2 ERROR]", e)

        finally:
            print("[ORCHESTRATOR V2 DONE]", round(time.time() - start, 2), "s")

    # -------------------------
    # HANDLER (runtime bridge)
    # -------------------------
    def _forward_to_runtime(self, signal):

        try:
            # runtime already pulls from queue,
            # this is just a trace hook

            self.bus.emit("signal_processed", signal)

        except Exception as e:
            print("[FORWARD ERROR]", e)
