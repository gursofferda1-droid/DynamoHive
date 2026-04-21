import time
import traceback
import hashlib

from backend.logger import logger
from backend.metrics_engine import update_metrics

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

        generated = 0
        skipped = 0
        signals = []
        decisions = []

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
            for item in crisis_signals:
                key = str(item.get("title", "")).lower()
                if key:
                    crisis_map[key] = item

            # -------------------------
            # 3. SIGNAL DETECTION
            # -------------------------
            signals = detect_signals(raw)

            if not signals:
                signals = [
                    {
                        "topic": str(x.get("title") or "fallback"),
                        "title": str(x.get("title") or "fallback"),
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
            for signal in signals:
                topic = str(signal.get("topic") or signal.get("title") or "").lower()

                if topic in crisis_map:
                    crisis = crisis_map[topic]
                    signal["urgency"] = crisis.get("urgency", "high")
                    signal["score"] = min(signal.get("score", 0.5) + 0.3, 1.0)

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
            for item in intel_items:
                try:
                    topic = str(item.get("topic") or "").strip()

                    if not topic:
                        skipped += 1
                        continue

                    if is_duplicate(topic):
                        skipped += 1
                        continue

                    decision = item.get("decision", {})
                    publish = decision.get("publish", False)

                    if not publish:
                        skipped += 1
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
                    skipped += 1
                    continue

            if generated == 0:
                logger.warning("[ORCHESTRATOR] NOTHING GENERATED")

        except Exception:
            traceback.print_exc()

        finally:
            duration = round(time.time() - start, 2)

            try:
                dominance = []

                for item in decisions[:5]:
                    decision = item.get("decision", {})
                    dominance.append({
                        "topic": item.get("topic", ""),
                        "dominance": decision.get("priority", 0)
                    })

                update_metrics({
                    "cycle_count": self.cycle,
                    "last_signal_count": len(signals),
                    "generated_count": generated,
                    "skipped_count": skipped,
                    "last_event_count": len(decisions),
                    "dominance": dominance,
                    "anomalies": [],
                    "last_duration": duration
                })

            except Exception as e:
                print("METRIC UPDATE ERROR:", e)

            logger.info(f"[ORCHESTRATOR] Cycle finished in {duration}s")
