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
                if not isinstance(signal, dict):
                    continue

                # -------------------------
                # TOPIC SAFE RESOLVE
                # -------------------------
                topic = str(
                    signal.get("topic")
                    or signal.get("title")
                    or signal.get("text")
                    or ""
                ).strip()

                if not topic:
                    continue

                print(f"[INTEL] PROCESSING: {topic}")

                # -------------------------
                # MEMORY
                # -------------------------
                try:
                    mem = self.memory.load(signal) or {}
                except:
                    mem = {}

                # -------------------------
                # CONTEXT
                # -------------------------
                try:
                    ctx = self.context.build(signal, mem) or {}
                except:
                    ctx = {}

                # -------------------------
                # REASONING
                # -------------------------
                try:
                    reasoning = self.reasoning.analyze(signal, ctx) or {}
                except:
                    reasoning = {}

                ctx["insight"] = reasoning.get("insight", "")

                # -------------------------
                # PREDICTION
                # -------------------------
                try:
                    prediction = self.prediction.forecast(signal, ctx) or {}
                except:
                    prediction = {}

                # -------------------------
                # INTEL OBJECT
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
                # NARRATIVE
                # -------------------------
                try:
                    narrative = generate_narrative(intel)
                except:
                    narrative = None

                if not narrative:
                    narrative = {
                        "title": topic[:80],
                        "content": topic,
                        "meta": {}
                    }

                intel["narrative"] = narrative

                results.append(intel)

            except Exception as e:
                print("[INTELLIGENCE ERROR]", e)
                continue

        print(f"[INTEL] OUTPUT COUNT: {len(results)}")

        return results
