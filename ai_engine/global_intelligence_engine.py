from backend.logger import logger

from ai_engine.memory_engine import MemoryEngine
from ai_engine.context_analyzer import ContextAnalyzer
from ai_engine.reasoning_engine import ReasoningEngine
from ai_engine.prediction_engine import PredictionEngine
from ai_engine.narrative_engine import generate_narrative


class GlobalIntelligenceEngine:

    def __init__(self):
        self.memory = MemoryEngine()
        self.context = ContextAnalyzer()
        self.reasoning = ReasoningEngine()
        self.prediction = PredictionEngine()

    def run(self, signals):

        results = []

        if not isinstance(signals, list) or not signals:
            return results

        for signal in signals:
            try:
                topic = str(
                    signal.get("topic") or
                    signal.get("title") or
                    signal.get("text") or
                    ""
                ).strip()

                if not topic:
                    logger.warning("[INTEL] Empty topic skipped")
                    continue

                logger.info(f"[INTEL] Processing: {topic}")

                # -------------------------
                # 1. MEMORY
                # -------------------------
                mem = self.memory.load(signal) or {}

                # -------------------------
                # 2. CONTEXT
                # -------------------------
                ctx = self.context.build(signal, mem) or {}

                # -------------------------
                # 3. REASONING
                # -------------------------
                reasoning = self.reasoning.analyze(signal, ctx) or {}

                ctx["insight"] = reasoning.get("insight", "")

                # -------------------------
                # 4. PREDICTION
                # -------------------------
                prediction = self.prediction.forecast(signal, ctx) or {}

                # -------------------------
                # 5. BUILD INTEL
                # -------------------------
                intel = {
                    "topic": topic,
                    "signal": signal,
                    "context": ctx,
                    "reasoning": reasoning,
                    "prediction": prediction,
                    "insight": reasoning.get("insight", ""),
                    "actors": ctx.get("actors", []),
                    "region": ctx.get("region", "global"),
                    "urgency": prediction.get("urgency", "low"),
                    "decision": signal.get("decision", {})
                }

                # -------------------------
                # 6. NARRATIVE
                # -------------------------
                narrative = generate_narrative(intel)

                if not isinstance(narrative, dict):
                    logger.warning(f"[INTEL] No narrative for: {topic}")
                    narrative = {}

                intel["narrative"] = {
                    "title": narrative.get("title") or topic[:120],
                    "content": narrative.get("content") or topic,
                    "meta": narrative.get("meta", {})
                }

                results.append(intel)

            except Exception as e:
                logger.warning(f"[INTEL ERROR] {e}")
                logger.warning(f"[FAILED SIGNAL] {signal}")
                continue

        logger.info(f"[INTEL] output={len(results)}")

        return results
