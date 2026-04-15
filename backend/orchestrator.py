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


# -------------------------
# DUPLICATE FILTER
# -------------------------
def is_duplicate(topic):
    try:
        time_bucket = int(time.time() / 300)
        h = hashlib.md5((str(topic).lower() + str(time_bucket)).encode()).hexdigest()
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
                        "topic": str(x.get("title") or "fallback"),
                        "score": 1.0,
                        "urgency": "low"
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
            # 6. 🔥 CRISIS ENRICHMENT (FIXED)
            # -------------------------
            for s in signals:

                topic = str(s.get("topic", "")).lower()

                for key, crisis in crisis_map.items():
                    if key in topic or topic in key:

                        # urgency overwrite
                        s["urgency"] = crisis.get("urgency", "high")

                        # 🔥 BOOST (daha güçlü yaptık)
                        s["score"] = min(s.get("score", 0.5) + 0.4, 1.0)

                        # attach full crisis data
                        s["crisis"] = crisis

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

            print("INTEL OUTPUT COUNT:", len(intel_items))

            # decision mapping FIX (index yerine topic ile)
            decision_map = {
                str(d.get("topic", "")).lower(): d.get("decision", {})
                for d in decisions
            }

            for item in intel_items:
                topic = str(item.get("topic", "")).lower()
                item["decision"] = decision_map.get(topic, {})

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

                    # 🔥 fallback (daha agresif publish)
                    publish = decision.get("publish", True)

                    if not publish:
                        print("SKIPPED:", topic)
                        continue

                    narrative = item.get("narrative") or {}

                    title = narrative.get("title") or topic[:80]
                    content = narrative.get("content") or topic

                    # 🔥 legal safe
                    source = item.get("source") or item.get("origin") or "Public Data"

                    content = f"""
{content}

---

Source: {source}
Disclaimer: AI-generated analysis.
"""

                    print("GENERATING:", title)

                    save_post(title, content)

                    generated += 1

                    logger.info(
                        f"[GENERATED] {topic} | priority={decision.get('priority', 'AUTO')}"
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
