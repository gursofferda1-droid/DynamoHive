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


def is_duplicate(topic: str) -> bool:
    try:
        bucket = int(time.time() / 300)
        key = f"{str(topic).lower()}_{bucket}"
        h = hashlib.md5(key.encode()).hexdigest()
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
                raw = LAST_DATA[-50:] if LAST_DATA else [{"title": "fallback signal"}]

            raw = process_data(raw)

            LAST_DATA.clear()
            LAST_DATA.extend(raw[:100])

            # -------------------------
            # 2. CRISIS DETECTION
            # -------------------------
            crisis_signals = detect_crisis_signals(raw) or []
            crisis_map = {
                str(c.get("title", "")).lower(): c
                for c in crisis_signals
            }

            # -------------------------
            # 3. SIGNALS
            # -------------------------
            signals = detect_signals(raw)

            if not signals:
                signals = [
                    {
                        "topic": str(x.get("title") or "fallback"),
                        "score": 1.0
                    }
                    for x in raw[:5]
                ]

            # -------------------------
            # 4. RANK
            # -------------------------
            signals = merge_ranked_signals(signals)

            # -------------------------
            # 5. CLUSTER
            # -------------------------
            signals = cluster_signals(signals) or []

            if not signals:
                logger.warning("[ORCHESTRATOR] No signals after clustering")
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
            # 7. DECISION
            # -------------------------
            decisions = self.decision.evaluate(signals) or []

            if not decisions:
                logger.warning("[ORCHESTRATOR] No decisions produced")
                return

            # -------------------------
            # 8. INTELLIGENCE
            # -------------------------
            intel_items = self.intelligence.run(decisions) or []

            if not intel_items:
                logger.warning("[ORCHESTRATOR] No intelligence output")
                return

            # decision sync fix
            for i, item in enumerate(intel_items):
                if i < len(decisions):
                    item["decision"] = decisions[i].get("decision", {})

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
                    publish = decision.get("publish", False)

                    if not publish:
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
                    logger.error(f"[GEN ERROR] {e}")
                    continue

            if generated == 0:
                logger.warning("[ORCHESTRATOR] NOTHING GENERATED")

        except Exception:
            traceback.print_exc()

        finally:
            duration = round(time.time() - start, 2)
            logger.info(f"[ORCHESTRATOR] Cycle finished in {duration}s")
