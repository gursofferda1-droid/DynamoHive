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
        key = hashlib.md5((str(topic).lower() + str(time_bucket)).encode()).hexdigest()
    except:
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
            # 2. CRISIS
            # -------------------------
            crisis_signals = detect_crisis_signals(raw)

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
                return []

            # -------------------------
            # 6. CRISIS ENRICHMENT
            # -------------------------
            for s in signals:
                topic = str(s.get("topic", "")).lower()

                if topic in crisis_map:
                    s["urgency"] = crisis_map[topic].get("urgency", "high")
                    s["score"] = min(s.get("score", 0.5) + 0.3, 1.0)

            # -------------------------
            # 7. DECISION
            # -------------------------
            decisions = self.decision.evaluate(signals)

            if not decisions:
                return []

            # -------------------------
            # 8. INTELLIGENCE
            # -------------------------
            intel_items = self.intelligence.run(decisions)

            if not intel_items:
                return []

            for i, item in enumerate(intel_items):
                if i < len(decisions):
                    item["decision"] = decisions[i].get("decision", {})

            # -------------------------
            # 9. GENERATION
            # -------------------------
            live_output = []

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

                    live_output.append({
                        "title": title,
                        "content": content,
                        "topic": topic,
                        "decision": decision
                    })

                    logger.info(f"[GENERATED] {topic}")

                except Exception as e:
                    skipped += 1
                    print("GEN ERROR:", e)

            # -------------------------
            # METRICS UPDATE
            # -------------------------
            try:
                update_metrics({
                    "cycle_count": self.cycle,
                    "last_signal_count": len(signals),
                    "generated_count": generated,
                    "skipped_count": skipped,
                    "last_event_count": len(decisions),
                    "dominance": [
                        {
                            "topic": d.get("topic"),
                            "dominance": d.get("decision", {}).get("priority", 0)
                        }
                        for d in intel_items[:5]
                    ],
                    "anomalies": []
                })
            except Exception as e:
                print("METRICS ERROR:", e)

            if generated == 0:
                logger.warning("[ORCHESTRATOR] NOTHING GENERATED")

            return live_output

        except Exception:
            traceback.print_exc()
            return []

        finally:
            duration = round(time.time() - start, 2)
            logger.info(f"[ORCHESTRATOR] Cycle finished in {duration}s")
