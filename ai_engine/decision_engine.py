class DecisionEngine:

    def evaluate(self, items):

        if not isinstance(items, list) or not items:
            return []

        scored = []

        # -------------------------
        # 1. SCORING PHASE
        # -------------------------
        for item in items:

            try:
                signal = item.get("signal", {})
                prediction = item.get("prediction", {})
                reasoning = item.get("reasoning", {})

                score = float(signal.get("score", 0) or 0)
                impact = float(prediction.get("impact_score", 0.5) or 0.5)

                confidence = 0.5
                if isinstance(reasoning, dict):
                    confidence = float(reasoning.get("confidence", 0.5) or 0.5)

                urgency = item.get("urgency", "low")

                urgency_map = {
                    "low": 0.3,
                    "medium": 0.6,
                    "high": 0.9
                }

                urgency_score = urgency_map.get(urgency, 0.3)

                # -------------------------
                # FINAL PRIORITY SCORE
                # -------------------------
                priority = (
                    (score * 0.30) +
                    (impact * 0.25) +
                    (confidence * 0.25) +
                    (urgency_score * 0.20)
                )

                # -------------------------
                # HARD FILTER (STABLE)
                # -------------------------
                if score < 0.10 and impact < 0.20:
                    continue

                scored.append({
                    "item": item,
                    "priority": priority,
                    "meta": {
                        "score": score,
                        "impact": impact,
                        "confidence": confidence,
                        "urgency": urgency
                    }
                })

            except Exception:
                continue

        if not scored:
            return []

        # -------------------------
        # 2. SORT
        # -------------------------
        scored.sort(key=lambda x: x["priority"], reverse=True)

        # -------------------------
        # 3. SELECTION RULES
        # -------------------------
        TOP_K = 5
        MIN_THRESHOLD = 0.30

        selected = []
        used_topics = set()

        for s in scored:

            if len(selected) >= TOP_K:
                break

            if s["priority"] < MIN_THRESHOLD:
                continue

            topic = str(s["item"].get("topic", "")).lower()

            if not topic or topic in used_topics:
                continue

            used_topics.add(topic)
            selected.append(s)

        # -------------------------
        # 4. FALLBACK (SAFE GUARANTEE)
        # -------------------------
        if not selected and scored:
            selected = [scored[0]]

        # -------------------------
        # 5. ATTACH DECISIONS
        # -------------------------
        output = []

        for idx, s in enumerate(scored):

            item = s["item"]

            publish = s in selected

            item["decision"] = {
                "publish": publish,
                "priority": round(s["priority"], 4),
                "rank": idx + 1,
                **s["meta"]
            }

            output.append(item)

        return output
