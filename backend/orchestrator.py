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


# -------------------------
# DUPLICATE CONTROL (FIXED)
# -------------------------
def is_duplicate(topic):
    try:
        # 🔥 daha kısa window (2 dk)
        time_bucket = int(time.time() / 120)
        h = hashlib.md5((str(topic[:50]).lower() + str(time_bucket)).encode()).hexdigest()
    except:
        return False

    now = time.time()

    if h in duplicate_cache and now - duplicate_cache[h] < 120:
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
                raw = LAST_DATA or [{"title": "fallback signal"}]

            raw = process_data(raw)

            LAST_DATA.clear()
            LAST_DATA.extend(raw[:100])

            # -------------------------
            # 2. CRISIS DETECTION
            # -------------------------
            crisis_signals = detect_crisis_signals(raw)
            print("CRISIS SIGNALS:", len(crisis_signals))

            crisis_map = []
            for c in crisis_signals:
                title = str(c.get("title", "")).lower()
                crisis_map.append((title, c))

            # -------------------------
            # 3. SIGNALS
            # -------------------------
            signals = detect_signals(raw)

            if not signals:
                signals = [
                    {"topic": str(x.get("title") or "fallback"), "score": 0.5}
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

                topic = str(s.get("topic") or "").lower()

                for title, crisis in crisis_map:

                    if topic and (topic in title or title in topic):

                        s["urgency"] = crisis.get("urgency", "high")

                        # 🔥 kontrollü boost
                        s["score"] = min(s.get("score", 0.4) + 0.2, 1.0)

                        s["crisis"] = True
                        break

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

            # decision attach
            for i, item in enumerate(intel_items):
                if i < len(decisions):
                    item["decision"] = decisions[i].get("decision", {})

            # -------------------------
            # 9. GENERATION (FIXED)
            # -------------------------
            generated = 0
            MIN_GENERATE = 2   # 🔥 en az üretim garantisi

            for item in intel_items:

                try:
                    topic = str(item.get("topic") or "").strip()

                    if not topic:
                        continue

                    # 🔥 duplicate soften
                    if is_duplicate(topic):
                        if generated > 0:
                            continue

                    decision = item.get("decision")
                    publish = True if not decision else decision.get("publish", False)

                    # 🔥 minimum içerik zorla
                    if not publish and generated >= MIN_GENERATE:
                        print("SKIPPED:", topic)
                        continue

                    narrative = item.get("narrative") or {}

                    title = narrative.get("title") or topic[:80]
                    content = narrative.get("content") or topic

                    source = item.get("source") or "Public Data"

                    content = f"""
{content}

---

Source: {source}
Disclaimer: This content is AI-generated analysis based on public data.
"""

                    print("GENERATING:", title)

                    save_post(title, content)

                    generated += 1

                    logger.info(
                        f"[GENERATED] {topic} | priority={decision.get('priority', 'N/A') if decision else 'FORCED'}"
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
