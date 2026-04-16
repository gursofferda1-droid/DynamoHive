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

DUPLICATE_WINDOW = 300
MAX_GENERATIONS_PER_CYCLE = 5


def cleanup_duplicate_cache():
    now = time.time()
    expired = [
        key for key, ts in duplicate_cache.items()
        if now - ts > DUPLICATE_WINDOW
    ]
    for key in expired:
        duplicate_cache.pop(key, None)


def is_duplicate(topic, content=""):
    try:
        cleanup_duplicate_cache()

        raw = f"{str(topic).lower()}|{str(content).lower()[:400]}"
        key = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        if key in duplicate_cache:
            return True

        duplicate_cache[key] = time.time()
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
            print("CRISIS SIGNALS:", len(crisis_signals))

            crisis_map = {
                str(c.get("title", "")).lower(): c
                for c in crisis_signals
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
                    for item in raw[:10]
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
                    s["urgency"] = "high"
                    s["score"] = min(float(s.get("score", 0.5)) + 0.3, 1.0)

            # -------------------------
            # 7. SORT BY SCORE
            # -------------------------
            signals = sorted(
                signals,
                key=lambda x: float(x.get("score", 0)),
                reverse=True
            )

            # -------------------------
            # 8. DECISION
            # -------------------------
            decisions = self.decision.evaluate(signals)

            if not decisions:
                logger.warning("[ORCHESTRATOR] No decisions")
                return

            # -------------------------
            # 9. INTELLIGENCE
            # -------------------------
            intel_items = self.intelligence.run(decisions)

            if not intel_items:
                logger.warning("[ORCHESTRATOR] No intelligence output")
                return

            for i, item in enumerate(intel_items):
                if i < len(decisions):
                    item["decision"] = decisions[i].get("decision", {})

            # -------------------------
            # 10. GENERATION
            # -------------------------
            generated = 0

            for item in intel_items:

                if generated >= MAX_GENERATIONS_PER_CYCLE:
                    break

                try:
                    topic = str(item.get("topic", "")).strip()

                    if not topic:
                        print("EMPTY TOPIC")
                        continue

                    narrative = item.get("narrative") or {}
                    title = narrative.get("title") or topic[:120]
                    content = narrative.get("content") or topic

                    if is_duplicate(topic, content):
                        print("DUPLICATE:", topic)
                        continue

                    decision = item.get("decision") or {}
                    publish = decision.get("publish")

                    if publish is None:
                        publish = True

                    if not publish:
                        print("SKIPPED:", topic)
                        continue

                    print("GENERATING:", title)

                    save_post(title, content)

                    generated += 1

                    logger.info(
                        f"[GENERATED] {topic} | "
                        f"priority={decision.get('priority', 'N/A')}"
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
            logger.info(
                f"[ORCHESTRATOR] Cycle finished in {duration}s"
            )
