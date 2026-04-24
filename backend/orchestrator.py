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
        key = hashlib.md5(
            (str(topic).lower() + str(time_bucket)).encode()
        ).hexdigest()
    except Exception:
        return False

    now = time.time()

    if key in duplicate_cache and now - duplicate_cache[key] < 300:
        return True

    duplicate_cache[key] = now
    return False


class Orchestrator:

    def __init__(self):
        self.cycle = 0
        self.intelligence = GlobalIntelligenceEngine()
        self.decision = DecisionEngine()

    def run_cycle(self):

        start = time.time()
        self.cycle += 1

        visible_items = []

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

            crisis_map = {}
            for item in crisis_signals:
                key = str(item.get("title", "")).lower()
                crisis_map[key] = item

            # -------------------------
            # 3. SIGNAL DETECTION
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
            # 4. RANKING
            # -------------------------
            signals = merge_ranked_signals(signals)

            # -------------------------
            # 5. CLUSTERING
            # -------------------------
            signals = cluster_signals(signals)

            if not signals:
                logger.warning("[ORCHESTRATOR] No signals after clustering")
                return []

            # -------------------------
            # 6. CRISIS BOOST
            # -------------------------
            for signal in signals:
                topic = str(signal.get("topic", "")).lower()

                if topic in crisis_map:
                    crisis = crisis_map[topic]
                    signal["urgency"] = crisis.get("urgency", "high")
                    signal["score"] = min(signal.get("score", 0.5) + 0.3, 1.0)

            # -------------------------
            # 7. DECISION
            # -------------------------
            decisions = self.decision.evaluate(signals)

            if not decisions:
                logger.warning("[ORCHESTRATOR] No decisions")
                return []

            # -------------------------
            # 8. INTELLIGENCE
            # -------------------------
            intel_items = self.intelligence.run(decisions)

            if not intel_items:
                logger.warning("[ORCHESTRATOR] No intelligence output")
                return []

            for i, item in enumerate(intel_items):
                if i < len(decisions):
                    item["decision"] = decisions[i].get("decision", {})

            # -------------------------
            # 9. GENERATION
            # -------------------------
            for item in intel_items:

                try:
                    topic = str(item.get("topic", "")).strip()

                    if not topic:
                        continue

                    if is_duplicate(topic):
                        continue

                    decision = item.get("decision", {})
                    publish = decision.get("publish", False)

                    if not publish:
                        continue

                    narrative = item.get("narrative", {})

                    title = narrative.get("title") or topic[:120]
                    content = narrative.get("content") or topic

                    save_post(title, content)

                    visible_items.append({
                        "topic": topic,
                        "title": title,
                        "content": content,
                        "priority": decision.get("priority", 0),
                        "score": item.get("score", 0),
                        "urgency": item.get("urgency", "normal")
                    })

                    logger.info(
                        f"[GENERATED] {topic} | priority={decision.get('priority', 0)}"
                    )

                except Exception as e:
                    logger.error(f"[GENERATION ERROR] {e}")
                    continue

            if not visible_items:
                logger.warning("[ORCHESTRATOR] NOTHING GENERATED")

            return visible_items

        except Exception:
            traceback.print_exc()
            return []

        finally:
            duration = round(time.time() - start, 2)
            logger.info(f"[ORCHESTRATOR] Cycle finished in {duration}s")
