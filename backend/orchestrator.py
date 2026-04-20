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


def is_duplicate(topic, ttl=3600):
    try:
        h = hashlib.md5(str(topic).strip().lower().encode()).hexdigest()
    except Exception:
        return False

    now = time.time()

    if h in duplicate_cache:
        if now - duplicate_cache[h] < ttl:
            return True

    duplicate_cache[h] = now
    return False


def cleanup_duplicate_cache(max_age=86400):
    now = time.time()
    stale_keys = [
        k for k, v in duplicate_cache.items()
        if now - v > max_age
    ]

    for k in stale_keys:
        duplicate_cache.pop(k, None)


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
                raw = LAST_DATA or [{"title": "fallback signal"}]

            raw = process_data(raw)

            LAST_DATA.clear()
            LAST_DATA.extend(raw[:100])

            # -------------------------
            # 2. CRISIS DETECTION
            # -------------------------
            crisis_signals = detect_crisis_signals(raw)
            logger.info(f"[CRISIS] signals={len(crisis_signals)}")

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
            decisions = self.decision.evaluate(signals)

            if not decisions:
                logger.warning("[ORCHESTRATOR] No decision output")
                return

            # publish edilecekleri ayır
            publish_items = [
                x for x in decisions
                if x.get("decision", {}).get("publish")
            ]

            if not publish_items:
                logger.warning("[ORCHESTRATOR] Nothing passed publish filter")
                return

            # -------------------------
            # 8. INTELLIGENCE
            # -------------------------
            intel_items = self.intelligence.run(publish_items)

            if not intel_items:
                logger.warning("[ORCHESTRATOR] No intelligence output")
                return

            # güvenli topic mapping
            decision_map = {
                str(x.get("topic", "")).lower(): x.get("decision", {})
                for x in publish_items
            }

            for item in intel_items:
                key = str(item.get("topic", "")).lower()
                item["decision"] = decision_map.get(key, {})

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
                        logger.info(f"[SKIPPED] {topic} | reason=duplicate_cache")
                        continue

                    decision = item.get("decision", {})
                    publish = decision.get("publish", False)

                    if not publish:
                        logger.info(
                            f"[SKIPPED] {topic} | reason={decision.get('reason','unknown')}"
                        )
                        continue

                    narrative = item.get("narrative") or {}

                    title = narrative.get("title") or topic[:80]
                    content = narrative.get("content") or topic

                    save_post(title, content)

                    generated += 1

                    logger.info(
                        f"[GENERATED] {topic} | "
                        f"priority={decision.get('priority','N/A')}"
                    )

                except Exception as e:
                    logger.warning(f"[GENERATION ERROR] {e}")
                    continue

            cleanup_duplicate_cache()

            logger.info(
                f"[FLOW] raw={len(raw)} "
                f"signals={len(signals)} "
                f"decisions={len(decisions)} "
                f"publish={len(publish_items)} "
                f"intel={len(intel_items)} "
                f"generated={generated}"
            )

            if generated == 0:
                logger.warning("[ORCHESTRATOR] NOTHING GENERATED")

        except Exception as e:
            logger.error(f"[ORCHESTRATOR ERROR] {e}")
            traceback.print_exc()

        finally:
            duration = round(time.time() - start, 2)
            logger.info(f"[ORCHESTRATOR] Cycle finished in {duration}s")
