import time
import traceback
import hashlib

from backend.logger import logger
from ai_engine.multi_crawler import crawl
from ai_engine.data_pipeline import process_data
from ai_engine.signal_detector import detect_signals
from ai_engine.signal_ranking_engine import merge_ranked_signals
from ai_engine.signal_cluster import cluster_signals
from ai_engine.global_intelligence_engine import GlobalIntelligenceEngine
from ai_engine.decision_engine import DecisionEngine
from ai_engine.global_crisis_radar import detect_crisis_signals
from backend.storage import save_post


LAST_DATA = []
duplicate_cache = {}


def is_duplicate(topic):
    try:
        bucket = int(time.time() / 300)
        h = hashlib.md5((str(topic).lower() + str(bucket)).encode()).hexdigest()
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

        # 🔥 TEK MERKEZ STATE (frontend bunu okur)
        self.state = {
            "cycle_count": 0,
            "last_signal_count": 0,
            "last_event_count": 0,
            "dominance": [],
            "anomalies": []
        }

    def run_cycle(self):

        start = time.time()
        self.cycle += 1

        try:
            # -------------------------
            # 1. DATA
            # -------------------------
            raw = crawl()

            if not raw:
                raw = LAST_DATA or [{"title": "fallback"}]

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
            signals = merge_ranked_signals(signals)
            signals = cluster_signals(signals)

            if not signals:
                return self.state

            # -------------------------
            # 4. CRISIS ENRICHMENT
            # -------------------------
            for s in signals:
                topic = str(s.get("topic", "")).lower()

                if topic in crisis_map:
                    c = crisis_map[topic]
                    s["urgency"] = c.get("urgency", "high")
                    s["score"] = min(s.get("score", 0.5) + 0.3, 1.0)

            # -------------------------
            # 5. DECISION + INTEL
            # -------------------------
            decisions = self.decision.evaluate(signals)
            intel_items = self.intelligence.run(decisions)

            # -------------------------
            # 6. DOMINANCE (UI FEED)
            # -------------------------
            dominance = [
                {
                    "topic": s.get("topic"),
                    "score": s.get("score", 0)
                }
                for s in signals[:10]
            ]

            # -------------------------
            # 7. UPDATE STATE (CRITICAL)
            # -------------------------
            self.state = {
                "cycle_count": self.cycle,
                "last_signal_count": len(signals),
                "last_event_count": len(crisis_signals),
                "dominance": dominance,
                "anomalies": crisis_signals[:5]
            }

            # -------------------------
            # 8. GENERATION
            # -------------------------
            for item in intel_items:

                try:
                    topic = item.get("topic")
                    if not topic or is_duplicate(topic):
                        continue

                    decision = item.get("decision", {})
                    if not decision.get("publish", False):
                        continue

                    narrative = item.get("narrative", {})

                    save_post(
                        narrative.get("title", topic[:80]),
                        narrative.get("content", topic)
                    )

                except Exception:
                    continue

            return self.state

        except Exception:
            traceback.print_exc()
            return self.state

        finally:
            logger.info(f"[ORCH] cycle={self.cycle} time={time.time()-start:.2f}s")
