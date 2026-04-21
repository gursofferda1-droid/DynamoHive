import time
import traceback
import hashlib

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
duplicate_cache = {}


def is_duplicate(topic):
    try:
        time_bucket = int(time.time() / 300)
        h = hashlib.md5((str(topic).lower() + str(time_bucket)).encode()).hexdigest()
    except:
        return False

    now = time.time()

    if h in duplicate_cache and now - duplicate_cache[h] < 300:
        return True

    duplicate_cache[h] = now
    return False


class Orchestrator:

    def __init__(self):
        self.cycle = 0
        self.intelligence = GlobalIntelligenceEngine()
        self.decision = DecisionEngine()

        # 🔥 SINGLE SOURCE OF TRUTH
        self.state = {
            "cycle_count": 0,
            "last_signal_count": 0,
            "last_event_count": 0,
            "dominance": [],
            "anomalies": [],
            "status": "running"
        }

    def run_cycle(self):

        start = time.time()
        self.cycle += 1

        logger.info(f"[ORCHESTRATOR] Cycle {self.cycle} started")

        try:
            # -------------------------
            # 1. DATA
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

            crisis_map = {}
            for c in crisis_signals:
                key = str(c.get("title", "")).lower()
                crisis_map[key] = c

            # -------------------------
            # 3. SIGNALS
            # -------------------------
            signals = detect_signals(raw)

            if not signals:
                signals = [
                    {"topic": str(x.get("title") or "fallback"), "score": 1.0}
                    for x in raw[:5]
                ]

            # -------------------------
            # 4. RANK
            # -------------------------
            signals = merge_ranked_signals(signals)

            # -------------------------
            # 5. CLUSTER
            # -------------------------
            signals = cluster_signals(signals)

            if not signals:
                logger.warning("[ORCHESTRATOR] No signals after clustering")
                return

            # -------------------------
            # 6. CRISIS BOOST
            # -------------------------
            for s in signals:

                topic = str(s.get("topic", "")).lower()

                if topic in crisis_map:
                    crisis = crisis_map[topic]
                    s["urgency"] = crisis.get("urgency", "high")
                    s["score"] = min(s.get("score", 0.5) + 0.3, 1.0)

            # -------------------------
            # 7. DECISION
            # -------------------------
            decisions = self.decision.evaluate(signals)

            if not decisions:
                logger.warning("[ORCHESTRATOR] No decisions")
                return

            # -------------------------
            # 8. INTELLIGENCE
            # -------------------------
            intel_items = self.intelligence.run(decisions)

            if not intel_items:
                logger.warning("[ORCHESTRATOR] No intelligence output")
                return

            for i, item in enumerate(intel_items):
                if i < len(decisions):
                    item["decision"] = decisions[i]

            # -------------------------
            # 9. GENERATION
            # -------------------------
            generated = 0

            for item in intel_items:

                try:
                    topic = str(item.get("topic") or "").strip()

                    if not topic:
                        continue

                    if is_duplicate(topic):
                        continue

                    decision = item.get("decision", {})
                    if not decision.get("publish", False):
                        continue

                    narrative = item.get("narrative") or {}

                    title = narrative.get("title") or topic[:80]
                    content = narrative.get("content") or topic

                    save_post(title, content)

                    generated += 1

                    logger.info(f"[GENERATED] {topic}")

                except Exception as e:
                    print("GEN ERROR:", e)

            # -------------------------
            # 10. STATE UPDATE (CRITICAL FIX)
            # -------------------------

            self.state["cycle_count"] = self.cycle
            self.state["last_signal_count"] = len(signals)
            self.state["last_event_count"] = len(crisis_signals)

            self.state["dominance"] = [
                {
                    "topic": s.get("topic"),
                    "score": s.get("score", 0)
                }
                for s in signals[:10]
            ]

            self.state["anomalies"] = [
                {
                    "type": c.get("type", "spike"),
                    "topic": c.get("title") or c.get("topic", "")
                }
                for c in crisis_signals[:5]
            ]

            print("GENERATED:", generated)

        except Exception:
            traceback.print_exc()

        finally:
            duration = round(time.time() - start, 2)
            logger.info(f"[ORCHESTRATOR] Cycle finished in {duration}s")
