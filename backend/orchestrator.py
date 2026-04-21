class Orchestrator:

    def __init__(self):
        self.cycle = 0
        self.intelligence = GlobalIntelligenceEngine()
        self.decision = DecisionEngine()

        # 🔥 TEK SOURCE OF TRUTH
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
            raw = crawl()

            if not raw:
                raw = LAST_DATA or [{"title": "fallback"}]

            raw = process_data(raw)
            LAST_DATA.clear()
            LAST_DATA.extend(raw[:100])

            crisis_signals = detect_crisis_signals(raw)

            signals = detect_signals(raw)
            signals = merge_ranked_signals(signals)
            signals = cluster_signals(signals)

            if not signals:
                return self.state

            # -------------------------
            # CRISIS ENRICHMENT
            # -------------------------
            for s in signals:
                topic = str(s.get("topic", "")).lower()

                for c in crisis_signals:
                    if topic == str(c.get("title", "")).lower():
                        s["urgency"] = c.get("urgency", "high")
                        s["score"] = min(s.get("score", 0.5) + 0.3, 1.0)

            # -------------------------
            # DECISION
            # -------------------------
            decisions = self.decision.evaluate(signals)

            intel_items = self.intelligence.run(decisions)

            # -------------------------
            # DOMINANCE MAP
            # -------------------------
            dominance = []

            for s in signals[:10]:
                dominance.append({
                    "topic": s.get("topic"),
                    "score": s.get("score", 0)
                })

            # -------------------------
            # STATE UPDATE (CRITICAL)
            # -------------------------
            self.state = {
                "cycle_count": self.cycle,
                "last_signal_count": len(signals),
                "last_event_count": len(crisis_signals),
                "dominance": dominance,
                "anomalies": crisis_signals[:5]
            }

            # -------------------------
            # GENERATION
            # -------------------------
            for item in intel_items:

                topic = item.get("topic")
                if not topic:
                    continue

                if is_duplicate(topic):
                    continue

                decision = item.get("decision", {})
                if not decision.get("publish", False):
                    continue

                narrative = item.get("narrative", {})

                save_post(
                    narrative.get("title", topic[:80]),
                    narrative.get("content", topic)
                )

            return self.state

        except Exception:
            traceback.print_exc()
            return self.state

        finally:
            logger.info(f"cycle {self.cycle} done in {time.time()-start:.2f}s")
