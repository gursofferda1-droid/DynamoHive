from ai_engine.memory_engine import MemoryEngine
from ai_engine.context_analyzer import ContextAnalyzer
from ai_engine.reasoning_engine import ReasoningEngine
from ai_engine.prediction_engine import PredictionEngine
from ai_engine.narrative_engine import generate_narrative

from backend.storage import store_feedback, get_state, set_state


class GlobalIntelligenceEngine:

    def __init__(self):
        self.memory = MemoryEngine()
        self.context = ContextAnalyzer()
        self.reasoning = ReasoningEngine()
        self.prediction = PredictionEngine()

        # 🔥 PLATFORM STATE
        self.state = get_state("intelligence_state") or {}

    def run(self, signals):

        results = []

        for signal in signals:

            try:
                topic = str(
                    signal.get("topic") or
                    signal.get("title") or
                    signal.get("text") or
                    ""
                ).strip()

                if not topic:
                    continue

                print("PROCESSING:", topic)

                # -------------------------
                # 1. MEMORY LOAD
                # -------------------------
                mem = self.memory.load(signal) or {}

                # 🔥 PLATFORM MEMORY AUGMENTATION
                mem["global_bias"] = self.state.get("bias", 0)

                # -------------------------
                # 2. CONTEXT BUILD
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
                # 5. INTELLIGENCE OBJECT
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
                # 6. NARRATIVE GENERATION
                # -------------------------
                narrative = generate_narrative(intel)

                if not narrative:
                    narrative = {
                        "title": topic[:80],
                        "content": topic,
                        "meta": {}
                    }

                intel["narrative"] = narrative

                # -------------------------
                # 7. PLATFORM MEMORY WRITE (KRİTİK EK)
                # -------------------------
                self._write_memory(signal, intel, prediction)

                results.append(intel)

            except Exception as e:
                print("INTELLIGENCE ERROR:", e)
                print("FAILED SIGNAL:", signal)
                continue

        print("INTEL OUTPUT COUNT:", len(results))

        # -------------------------
        # 8. STATE UPDATE (GLOBAL LEARNING)
        # -------------------------
        self._update_state(results)

        return results

    # -------------------------
    # MEMORY FEEDBACK LOOP
    # -------------------------
    def _write_memory(self, signal, intel, prediction):

        try:
            store_feedback(
                post_title=intel.get("narrative", {}).get("title", ""),
                signal_topic=intel.get("topic", ""),
                engagement_score=prediction.get("confidence", 0.0),
                outcome="generated",
                raw={
                    "region": intel.get("region"),
                    "urgency": intel.get("urgency"),
                    "actors": intel.get("actors")
                }
            )
        except:
            pass

    # -------------------------
    # GLOBAL STATE EVOLUTION
    # -------------------------
    def _update_state(self, results):

        try:
            if not results:
                return

            avg_urgency = 0
            count = 0

            urgency_map = {"low": 0.3, "medium": 0.6, "high": 0.9}

            for r in results:
                u = r.get("urgency", "low")
                avg_urgency += urgency_map.get(u, 0.3)
                count += 1

            avg_urgency = avg_urgency / max(count, 1)

            current = self.state or {}

            # 🔥 adaptive intelligence bias
            current["bias"] = avg_urgency

            set_state("intelligence_state", current)

        except:
            pass
