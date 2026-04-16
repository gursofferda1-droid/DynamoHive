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


def normalize_topic(topic):
    return str(topic).strip().lower()


def is_duplicate(topic):
    try:
        key = hashlib.md5(normalize_topic(topic).encode()).hexdigest()
    except:
        return False

    now = time.time()
    ttl = 1800  # 30 dakika

    expired = [
        k for k, ts in duplicate_cache.items()
        if now - ts > ttl
    ]

    for k in expired:
        duplicate_cache.pop(k, None)

    if key in duplicate_cache:
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

        logger.info(f"[ORCHESTRATOR] Cycle {self.cycle} started")

        try:
            # -------------------------
            # 1. DATA
            # -------------------------
            raw = crawl()

            if not raw:
                if LAST_DATA:
                    raw = LAST_DATA[:]
                else:
                    raw = [{"title": "fallback signal"}]

            raw = process_data(raw)

            LAST_DATA.clear()
            LAST_DATA.extend(raw[:100])

            # -------------------------
            # 2. CRISIS DETECTION
            # -------------------------
            crisis_signals = detect_crisis_signals(raw)
            print("CRISIS SIGNALS:", len(crisis_signals))

            crisis_map = {}

            for c in crisis_signals:
                key = normalize_topic(
                    c.get("topic") or c.get("title", "")
                )
                if key:
                    crisis_map[key] = c

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
            signals = cluster_signals(signals)

            if not signals:
                logger.warning("[ORCHESTRATOR] No signals after clustering")
                return

            # -------------------------
            # 6. CRISIS ENRICHMENT
            # -------------------------
            for s in signals:
                topic = normalize_topic(s.get("topic", ""))

                if topic in crisis_map:
                    crisis = crisis_map[topic]

                    s["urgency"] = crisis.get("urgency", "high")
                    s["score"] = min(s.get("score", 0.5) + 0.3, 1.0)

            # -------------------------
            # 7. DECISION
            # -------------------------
            decisions = self.decision.evaluate(signals)

            if not decisions:
                logger.warning("[ORCHESTRATOR] No signals passed decision filter")
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
                    item["decision"] = decisions[i].get("decision", {})

            # -------------------------
            # 9. GENERATION
            # -------------------------
            generated = 0

            for item in intel_items:
                try:
                    topic = normalize_topic(item.get("topic"))

                    if not topic:
                        continue

                    if is_duplicate(topic):
                        print("DUPLICATE:", topic)
                        continue

                    decision = item.get("decision", {})
                    publish = decision.get("publish", False)

                    if not publish:
                        print("SKIPPED:", topic)
                        continue

                    narrative = item.get("narrative") or {}

                    title = narrative.get("title") or topic[:80]
                    content = narrative.get("content") or topic

                    print("GENERATING:", title)

                    save_post(title, content)

                    generated += 1

                    logger.info(
                        f"[GENERATED] {topic} | priority={decision.get('priority', 'N/A')}"
                    )

                except Exception as e:
                    print("GEN ERROR:", e)
                    continue

            print("GENERATED COUNT:", generated)

            if generated == 0:
                logger.warning("[ORCHESTRATOR] NOTHING GENERATED")

        except Exception:
            traceback.print_exc()

        finally:
            duration = round(time.time() - start, 2)
            logger.info(f"[ORCHESTRATOR] Cycle finished in {duration}s")
