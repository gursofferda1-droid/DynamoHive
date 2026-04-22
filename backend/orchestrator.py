import time
import traceback
import hashlib

from backend.logger import logger

from ai_engine.multi_crawler import crawl
from ai_engine.data_pipeline import process_data
from ai_engine.signal_detector import detect_signals
from ai_engine.signal_ranking_engine import merge_ranked_signals
from ai_engine.signal_cluster import cluster_signals
from ai_engine.global_crisis_radar import detect_crisis_signals
from ai_engine.global_intelligence_engine import GlobalIntelligenceEngine
from ai_engine.decision_engine import DecisionEngine

from backend.storage import save_post


LAST_DATA = []
duplicate_cache = {}


def is_duplicate(topic: str, ttl: int = 300) -> bool:
    try:
        normalized = str(topic).strip().lower()
        if not normalized:
            return True

        time_bucket = int(time.time() / ttl)
        key = hashlib.md5(f"{normalized}:{time_bucket}".encode()).hexdigest()

        now = time.time()

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
            # ---------------------------------
            # 1. DATA COLLECTION
            # ---------------------------------
            raw = crawl()

            if not raw:
                logger.warning("[ORCHESTRATOR] crawler returned empty, using cached data")
                raw = LAST_DATA.copy()

            if not raw:
                logger.warning("[ORCHESTRATOR] no usable input data")
                return

            raw = process_data(raw)

            if not raw:
                logger.warning("[ORCHESTRATOR] process_data returned empty")
                return

            LAST_DATA.clear()
            LAST_DATA.extend(raw[:100])

            # ---------------------------------
            # 2. CRISIS DETECTION
            # ---------------------------------
            crisis_signals = detect_crisis_signals(raw) or []

            crisis_map = {
                str(item.get("title", "")).strip().lower(): item
                for item in crisis_signals
                if item.get("title")
            }

            logger.info(f"[CRISIS] detected={len(crisis_signals)}")

            # ---------------------------------
            # 3. SIGNAL DETECTION
            # ---------------------------------
            signals = detect_signals(raw)

            if not signals:
                signals = [
                    {
                        "topic": str(item.get("title") or "").strip(),
                        "score": 0.5
                    }
                    for item in raw[:5]
                    if item.get("title")
                ]

            if not signals:
                logger.warning("[ORCHESTRATOR] no signals detected")
                return

            # ---------------------------------
            # 4. RANKING
            # ---------------------------------
            signals = merge_ranked_signals(signals)

            # ---------------------------------
            # 5. CLUSTERING
            # ---------------------------------
            signals = cluster_signals(signals)

            if not signals:
                logger.warning("[ORCHESTRATOR] no signals after clustering")
                return

            # ---------------------------------
            # 6. CRISIS ENRICHMENT
            # ---------------------------------
            for signal in signals:
                topic_key = str(signal.get("topic", "")).strip().lower()

                if topic_key in crisis_map:
                    crisis = crisis_map[topic_key]

                    signal["urgency"] = crisis.get("urgency", "high")
                    signal["score"] = min(
                        float(signal.get("score", 0.5)) + 0.25,
                        1.0
                    )

            # ---------------------------------
            # 7. DECISION
            # ---------------------------------
            decisions = self.decision.evaluate(signals)

            if not decisions:
                logger.warning("[ORCHESTRATOR] decision engine rejected all signals")
                return

            # ---------------------------------
            # 8. INTELLIGENCE
            # ---------------------------------
            intel_items = self.intelligence.run(decisions)

            if not intel_items:
                logger.warning("[ORCHESTRATOR] intelligence returned empty")
                return

            for idx, item in enumerate(intel_items):
                if idx < len(decisions):
                    item["decision"] = decisions[idx].get("decision", {})

            # ---------------------------------
            # 9. GENERATION
            # ---------------------------------
            generated = 0

            for item in intel_items:
                try:
                    topic = str(item.get("topic") or "").strip()

                    if not topic:
                        continue

                    if is_duplicate(topic):
                        continue

                    decision = item.get("decision") or {}
                    score = float(item.get("score", 0))

                    publish = decision.get("publish")

                    if publish is None:
                        publish = score >= 0.35

                    if not publish:
                        logger.info(f"[SKIPPED] {topic}")
                        continue

                    narrative = item.get("narrative") or {}

                    title = str(
                        narrative.get("title") or topic[:120]
                    ).strip()

                    content = str(
                        narrative.get("content") or topic
                    ).strip()

                    if not title or not content:
                        continue

                    save_post(title, content)

                    generated += 1

                    logger.info(
                        f"[GENERATED] {topic} | priority={decision.get('priority', 'auto')}"
                    )

                except Exception as e:
                    logger.exception(f"[GENERATION ERROR] {e}")

            logger.info(f"[ORCHESTRATOR] generated={generated}")

            if generated == 0:
                logger.warning("[ORCHESTRATOR] no content generated")

        except Exception:
            logger.exception("[ORCHESTRATOR] fatal cycle error")

        finally:
            duration = round(time.time() - start, 2)
            logger.info(f"[ORCHESTRATOR] Cycle finished in {duration}s")
