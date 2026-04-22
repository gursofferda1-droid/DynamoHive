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

        if not isinstance(signals, list):
            return results

        for signal in signals:

            try:
                # -------------------------
                # TOPIC NORMALIZATION
                # -------------------------
                topic = str(
                    signal.get("topic")
                    or signal.get("title")
                    or signal.get("text")
                    or ""
                ).strip()

                if not topic:
                    print("[INTEL] SKIP EMPTY TOPIC:", signal)
                    continue

                # -------------------------
                # MEMORY
                # -------------------------
                mem = self.memory.load(signal) or {}

                # -------------------------
                # CONTEXT
                # -------------------------
                ctx = self.context.build(signal, mem) or {}

                # -------------------------
                # REASONING
                # -------------------------
                reasoning = self.reasoning.analyze(signal, ctx) or {}

                ctx["insight"] = reasoning.get("insight", "")

                # -------------------------
                # PREDICTION
                # -------------------------
                prediction = self.prediction.forecast(signal, ctx) or {}

                # -------------------------
                # INTELLIGENCE OBJECT
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
                }

                # -------------------------
                # NARRATIVE GENERATION
                # -------------------------
                narrative = generate_narrative(intel)

                if not narrative:
                    narrative = {
                        "title": topic[:80],
                        "content": topic,
                        "meta": {}
                    }

                intel["narrative"] = narrative

                results.append(intel)

            except Exception as e:
                print("[INTEL ERROR]", e)
                print("[FAILED SIGNAL]", signal)
                continue

        print("[INTEL] OUTPUT COUNT:", len(results))
        return results
