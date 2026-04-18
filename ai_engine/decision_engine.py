class DecisionEngine:

    def evaluate(self, items):

        if not isinstance(items, list) or not items:
            return []

        scored = []

        # -------------------------
        # 1. SCORING (soft system)
        # -------------------------
        for item in items:

            try:
                signal = item.get("signal", {})
                prediction = item.get("prediction", {})
                reasoning = item.get("reasoning", {})

                score = float(signal.get("score", 0.3))
                impact = float(prediction.get("impact_score", 0.4))
                confidence = float(reasoning.get("confidence", 0.5)) if isinstance(reasoning, dict) else 0.5

                urgency_map = {"low": 0.2, "medium": 0.5, "high": 0.8}
                urgency = urgency_map.get(item.get("urgency", "medium"), 0.5)

                # soft composite score
                priority = (
                    score * 0.35 +
                    impact * 0.30 +
                    confidence * 0.20 +
                    urgency * 0.15
                )

                scored.append({
                    "item": item,
                    "priority": priority,
                    "meta": {
                        "score": score,
                        "impact": impact,
                        "confidence": confidence,
                        "urgency": item.get("urgency", "medium")
                    }
                })

            except:
                continue

        if not scored:
            return []

        # -------------------------
        # 2. SORT
        # -------------------------
        scored.sort(key=lambda x: x["priority"], reverse=True)

        # -------------------------
        # 3. SELECTION (guaranteed output)
        # -------------------------
        TOP_K = 5
        MIN_SOFT = 0.15

        selected = []
        seen_topics = set()

        for s in scored:

            topic = str(s["item"].get("topic", "")).lower()

            if topic in seen_topics:
                continue

            seen_topics.add(topic)

            # soft filter (NOT hard block)
            if s["priority"] < MIN_SOFT and len(selected) > 0:
                continue

            selected.append(s)

            if len(selected) >= TOP_K:
                break

        # -------------------------
        # 4. FALLBACK GUARANTEE (CRITICAL FIX)
        # -------------------------
        if not selected:
            selected = [scored[0]]

        # -------------------------
        # 5. DECISION ATTACHMENT
        # -------------------------
        output = []

        for idx, s in enumerate(scored):

            item = s["item"]
            publish = s in selected

            item["decision"] = {
                "publish": publish,
                "priority": round(s["priority"], 3),
                "rank": idx + 1,
                **s["meta"]
            }

            output.append(item)

        return output
