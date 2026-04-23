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

DUPLICATE_TTL = 3600
MAX_CACHE_SIZE = 5000


def cleanup_duplicate_cache():
    now = time.time()

    expired = [
        key for key, ts in duplicate_cache.items()
        if now - ts > DUPLICATE_TTL
    ]

    for key in expired:
        duplicate_cache.pop(key, None)

    if len(duplicate_cache) > MAX_CACHE_SIZE:
        sorted_items = sorted(
            duplicate_cache.items(),
            key=lambda x: x[1]
        )

        overflow = len(duplicate_cache) - MAX_CACHE_SIZE

        for key, _ in sorted_items[:overflow]:
            duplicate_cache.pop(key, None)


def is_duplicate(topic):
    try:
        key = hashlib.md5(
            str(topic).lower().strip().encode()
        ).hexdigest()

        now = time.time()

        if key in duplicate_cache:
            if now - duplicate_cache[key] < DUPLICATE_TTL:
                return True

        duplicate_cache[key] = now
        return False

    except Exception:
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
            cleanup_duplicate_cache()

            # -------------------------
            # 1. DATA COLLECTION
            # -------------------------
            raw = crawl()

            if not raw:
                logger.warning("[ORCHESTRATOR] No fresh raw data")
                return

            raw = process_data(raw)

            if not raw:
                logger.warning("[ORCHESTRATOR] No processed data")
                return

            LAST_DATA.clear()
            LAST_DATA.extend(raw[:100])

            # -------------------------
            # 2. CRISIS DETECTION
            # -------------------------
            crisis_signals = detect_crisis_signals(raw)

            crisis_map = {}
            for item in crisis_signals:
                title = str(item.get("title", "")).lower().strip()
                if title:
                    crisis_map[title] = item

            # -------------------------
            # 3. SIGNAL DETECTION
            # -------------------------
            signals = detect_signals(raw)

            if not signals:
                logger.warning("[ORCHESTRATOR] No detected signals")
                return

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
            # 6. CRISIS ENRICHMENT
            # -------------------------
            for signal in signals:
                topic = str(signal.get("topic", "")).lower().strip()

                for crisis_title, crisis_data in crisis_map.items():
                    if topic in crisis_title or crisis_title in topic:
                        signal["urgency"] = crisis_data.get("urgency", "high")
                        signal["score"] = min(
                            signal.get("score", 0.5) + 0.30,
                            1.0
                        )
                        break

            # -------------------------
            # 7. DECISION
            # -------------------------
            decisions = self.decision.evaluate(signals)

            if not decisions:
                logger.warning("[ORCHESTRATOR] No decision output")
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
                    topic = str(item.get("topic", "")).strip()

                    if not topic:
                        continue

                    if is_duplicate(topic):
                        continue

                    decision = item.get("decision", {})

                    priority = float(
                        decision.get("priority", 0)
                    )

                    publish = (
                        decision.get("publish", False)
                        or priority >= 0.25
                    )

                    if not publish:
                        continue

                    narrative = item.get("narrative", {})

                    title = narrative.get("title") or topic[:120]
                    content = narrative.get("content") or topic

                    save_post(title, content)

                    generated += 1

                    logger.info(
                        f"[GENERATED] {title} | priority={priority}"
                    )

                except Exception as e:
                    logger.error(f"[GENERATION ERROR] {e}")
                    continue

            if generated == 0:
                logger.warning("[ORCHESTRATOR] NOTHING GENERATED")
            else:
                logger.info(
                    f"[ORCHESTRATOR] Generated {generated} posts"
                )

        except Exception:
            logger.error(traceback.format_exc())

        finally:
            duration = round(time.time() - start, 2)
            logger.info(
                f"[ORCHESTRATOR] Cycle finished in {duration}s"
            )
