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

        for signal in signals:

            try:
                topic = (
                    signal.get("topic")
                    or signal.get("title")
                    or signal.get("text")
                    or ""
                ).strip()

                if not topic:
                    continue

                mem = self.memory.load(signal) or {}
                ctx = self.context.build(signal, mem) or {}
                reasoning = self.reasoning.analyze(signal, ctx) or {}

                ctx["insight"] = reasoning.get("insight", "")

                prediction = self.prediction.forecast(signal, ctx) or {}

                intel = {
                    "topic": topic,
                    "signal": signal,
                    "context": ctx,
                    "reasoning": reasoning,
                    "prediction": prediction,
                    "urgency": prediction.get("urgency", "low"),
                }

                narrative = generate_narrative(intel)

                intel["narrative"] = narrative or {
                    "title": topic[:80],
                    "content": topic
                }

                results.append(intel)

            except Exception as e:
                print("INTELLIGENCE ERROR:", e)

        return results
