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


def is_duplicate(topic):
    try:
        now = time.time()
        bucket = int(now / 300)
        key = hashlib.md5((str(topic).lower() + str(bucket)).encode()).hexdigest()

        if key in duplicate_cache and (now - duplicate_cache[key]) < 300:
            return True

        duplicate_cache[key] = now
        return False

    except:
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
            raw = crawl() or LAST_DATA or [{"title": "fallback"}]
            raw = process_data(raw)

            LAST_DATA.clear()
            LAST_DATA.extend(raw[:100])

            crisis_signals = detect_crisis_signals(raw)
            crisis_map = {
                str(c.get("title", "")).lower(): c
                for c in crisis_signals
            }

            signals = detect_signals(raw)

            if not signals:
                signals = [{"topic": x.get("title", "fallback"), "score": 1.0} for x in raw[:5]]

            signals = merge_ranked_signals(signals)
            signals = cluster_signals(signals)

            if not signals:
                return

            for s in signals:
                t = str(s.get("topic", "")).lower()
                if t in crisis_map:
                    s["urgency"] = crisis_map[t].get("urgency", "high")
                    s["score"] = min(s.get("score", 0.5) + 0.3, 1.0)

            decisions = self.decision.evaluate(signals)
            if not decisions:
                return

            intel = self.intelligence.run(decisions)
            if not intel:
                return

            for i, item in enumerate(intel):
                if i < len(decisions):
                    item["decision"] = decisions[i].get("decision", {})

            generated = 0

            for item in intel:

                topic = str(item.get("topic", "")).strip()
                if not topic or is_duplicate(topic):
                    continue

                decision = item.get("decision", {})
                if not decision.get("publish", False):
                    continue

                narrative = item.get("narrative", {})

                title = narrative.get("title", topic[:80])
                content = narrative.get("content", topic)

                save_post(title, content)
                generated += 1

                logger.info(f"[GENERATED] {topic}")

            logger.info(f"[ORCHESTRATOR] generated={generated}")

        except Exception:
            traceback.print_exc()

        finally:
            logger.info(f"[ORCHESTRATOR] cycle done in {round(time.time()-start,2)}s")
