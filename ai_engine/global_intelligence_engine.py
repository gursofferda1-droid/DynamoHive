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
                # 1. TOPIC NORMALIZATION
                # -------------------------
                topic = str(
                    signal.get("topic")
                    or signal.get("title")
                    or signal.get("text")
                    or ""
                ).strip()

                if not topic:
                    continue

                # -------------------------
                # 2. MEMORY LAYER
                # -------------------------
                memory = self.memory.load(signal)
                if memory is None:
                    memory = {}

                # -------------------------
                # 3. CONTEXT BUILD
                # -------------------------
                context = self.context.build(signal, memory)
                if context is None:
                    context = {}

                # -------------------------
                # 4. REASONING
                # -------------------------
                reasoning = self.reasoning.analyze(signal, context)
                if reasoning is None:
                    reasoning = {}

                context["insight"] = reasoning.get("insight", "")

                # -------------------------
                # 5. PREDICTION
                # -------------------------
                prediction = self.prediction.forecast(signal, context)
                if prediction is None:
                    prediction = {}

                # -------------------------
                # 6. INTELLIGENCE OBJECT
                # -------------------------
                intel = {
                    "topic": topic,
                    "signal": signal,
                    "context": context,
                    "reasoning": reasoning,
                    "prediction": prediction,
                    "insight": reasoning.get("insight", ""),
                    "actors": context.get("actors", []),
                    "region": context.get("region", "global"),
                    "urgency": prediction.get("urgency", "low"),
                }

                # -------------------------
                # 7. NARRATIVE
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
                # kritik: sessiz fail değil, kontrollü fail
                print("[INTELLIGENCE ERROR]", e)
                continue

        return results
