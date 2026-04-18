import time
import traceback

from backend.logger import logger

from ai_engine.multi_crawler import crawl
from ai_engine.data_pipeline import process_data
from ai_engine.signal_detector import detect_signals
from ai_engine.signal_ranking_engine import merge_ranked_signals

from ai_engine.global_intelligence_engine import GlobalIntelligenceEngine
from ai_engine.decision_engine import DecisionEngine
from ai_engine.signal_cluster import cluster_signals
from ai_engine.global_crisis_radar import detect_crisis_signals

from backend.storage import save_post


LAST_DATA = []


class Orchestrator:

    def __init__(self):
        self.cycle = 0
        self.intelligence = GlobalIntelligenceEngine()
        self.decision = DecisionEngine()

    def run_cycle(self):

        start = time.time()
        self.cycle += 1

        logger.info(f"[ORCHESTRATOR] Cycle {self.cycle} started")

        try:
            # -------------------------
            # 1. DATA COLLECTION
            # -------------------------
            raw = crawl()

            if not raw:
                raw = LAST_DATA or [{"title": "fallback signal"}]

            raw = process_data(raw)

            LAST_DATA.clear()
            LAST_DATA.extend(raw[:100])

            # -------------------------
            # 2. CRISIS DETECTION
            # -------------------------
            crisis_signals = detect_crisis_signals(raw)

            crisis_map = {
                str(item.get("title", "")).lower().strip(): item
                for item in crisis_signals
            }

            # -------------------------
            # 3. SIGNAL DETECTION
            # -------------------------
            signals = detect_signals(raw)

            if not signals:
                signals = [
                    {
                        "topic": str(item.get("title") or "fallback"),
                        "score": 0.5
                    }
                    for item in raw[:5]
                ]

            # -------------------------
            # 4. RANKING
            # -------------------------
            signals = merge_ranked_signals(signals)

            # -------------------------
            # 5. CLUSTERING
            # -------------------------
            signals = cluster_signals(signals)

            if not signals:
                logger.warning("[ORCHESTRATOR] No signals after clustering")
                return

            # -------------------------
            # 6. CRISIS BOOST
            # -------------------------
            for signal in signals:
                topic = str(signal.get("topic", "")).lower().strip()

                if topic in crisis_map:
                    signal["urgency"] = crisis_map[topic].get("urgency", "high")
                    signal["score"] = min(float(signal.get("score", 0.5)) + 0.25, 1.0)

            # -------------------------
            # 7. DECISION
            # -------------------------
            decisions = self.decision.evaluate(signals)

            if not decisions:
                decisions = signals

            # -------------------------
            # 8. INTELLIGENCE
            # -------------------------
            intel_items = self.intelligence.run(decisions)

            if not intel_items:
                logger.warning("[ORCHESTRATOR] No intelligence output")
                return

            # attach decision data
            for i, item in enumerate(intel_items):
                if i < len(decisions):
                    item["decision"] = decisions[i].get("decision", {})

            # -------------------------
            # 9. GENERATION
            # -------------------------
            generated = 0

            for item in intel_items:
                try:
                    topic = str(item.get("topic", "")).strip()

                    if not topic:
                        continue

                    decision = item.get("decision", {})
                    priority = float(decision.get("priority", 0))
                    publish = decision.get("publish", None)

                    # fallback publish logic
                    if publish is False and priority < 0.25:
                        logger.info(f"[SKIPPED] {topic}")
                        continue

                    narrative = item.get("narrative", {})

                    title = narrative.get("title") or topic[:120]
                    content = narrative.get("content") or topic

                    saved = save_post(title, content)

                    if not saved:
                        logger.info(f"[SKIPPED DUPLICATE] {title}")
                        continue

                    generated += 1

                    logger.info(
                        f"[GENERATED] {title} | priority={priority}"
                    )

                except Exception as e:
                    logger.error(f"[GEN ERROR] {e}")

            if generated == 0:
                logger.warning("[ORCHESTRATOR] NOTHING GENERATED")

        except Exception:
            traceback.print_exc()

        finally:
            duration = round(time.time() - start, 2)
            logger.info(f"[ORCHESTRATOR] Cycle finished in {duration}s")
