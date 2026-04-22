import time
import traceback
import hashlib

from backend.logger import logger

from ai_engine.multi_crawler import crawl
from ai_engine.data_pipeline import process_data
from ai_engine.signal_detector import detect_signals
from ai_engine.signal_ranking_engine import merge_ranked_signals
from ai_engine.signal_cluster import cluster_signals

from ai_engine.global_intelligence_engine import GlobalIntelligenceEngine
from ai_engine.decision_engine import DecisionEngine
from ai_engine.global_crisis_radar import detect_crisis_signals

from backend.storage import save_post


# -------------------------
# MEMORY
# -------------------------
LAST_DATA = []
duplicate_cache = {}


# -------------------------
# DUPLICATE GUARD
# -------------------------
def is_duplicate(topic: str) -> bool:
    try:
        now = time.time()
        bucket = int(now / 300)

        key = hashlib.md5(
            (str(topic).lower() + str(bucket)).encode()
        ).hexdigest()

        if key in duplicate_cache and (now - duplicate_cache[key]) < 300:
            return True

        duplicate_cache[key] = now
        return False

    except:
        return False


# -------------------------
# ORCHESTRATOR
# -------------------------
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
            # 1. CRAWL
            # -------------------------
            raw = crawl()

            if not raw:
                raw = LAST_DATA or [{"title": "fallback signal"}]

            # -------------------------
            # 2. PROCESS
            # -------------------------
            raw = process_data(raw)

            LAST_DATA.clear()
            LAST_DATA.extend(raw[:100])

            # -------------------------
            # 3. CRISIS DETECTION
            # -------------------------
            crisis_signals = detect_crisis_signals(raw)

            crisis_map = {
                str(c.get("title", "")).lower(): c
                for c in crisis_signals
            }

            # -------------------------
            # 4. SIGNAL DETECTION
            # -------------------------
            signals = detect_signals(raw)

            if not signals:
                signals = [
                    {
                        "topic": x.get("title", "fallback"),
                        "score": 1.0
                    }
                    for x in raw[:5]
                ]

            # -------------------------
            # 5. RANK + CLUSTER
            # -------------------------
            signals = merge_ranked_signals(signals)
            signals = cluster_signals(signals)

            if not signals:
                logger.warning("[ORCHESTRATOR] no signals after clustering")
                return

            # -------------------------
            # 6. CRISIS ENRICHMENT
            # -------------------------
            for s in signals:
                topic = str(s.get("topic", "")).lower()

                if topic in crisis_map:
                    crisis = crisis_map[topic]

                    s["urgency"] = crisis.get("urgency", "high")
                    s["score"] = min(s.get("score", 0.5) + 0.3, 1.0)

            # -------------------------
            # 7. DECISION ENGINE
            # -------------------------
            decisions = self.decision.evaluate(signals)

            if not decisions:
                logger.warning("[ORCHESTRATOR] no decisions passed filter")
                return

            # -------------------------
            # 8. INTELLIGENCE ENGINE
            # -------------------------
            intel_items = self.intelligence.run(decisions)

            if not intel_items:
                logger.warning("[ORCHESTRATOR] no intelligence output")
                return

            # attach decision back
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

                    logger.info(
                        f"[GENERATED] {topic} | priority={decision.get('priority', 'N/A')}"
                    )

                except Exception as e:
                    print("GEN ERROR:", e)
                    continue

            logger.info(f"[ORCHESTRATOR] generated={generated}")

        except Exception:
            traceback.print_exc()

        finally:
            duration = round(time.time() - start, 2)
            logger.info(f"[ORCHESTRATOR] Cycle finished in {duration}s")
