class DecisionEngine:

    def evaluate(self, items):

        if not isinstance(items, list) or not items:
            return []

        scored = []

        # -------------------------
        # 1. SCORING
        # -------------------------
        for item in items:

            try:
                signal = item.get("signal", {}) or {}
                prediction = item.get("prediction", {}) or {}
                reasoning = item.get("reasoning", {}) or {}

                score = float(signal.get("score", 0) or 0)
                impact = float(prediction.get("impact_score", 0.5) or 0.5)
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
                    score * 0.30 +
                    impact * 0.25 +
                    confidence * 0.25 +
                    urgency_score * 0.20
                )

                # -------------------------
                # FILTER
                # -------------------------
                if score < 0.15 and impact < 0.25:
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
        # 3. SELECTION
        # -------------------------
        TOP_K = 5
        MIN_THRESHOLD = 0.25

        selected = []
        used_topics = set()

        for s in scored:

            if len(selected) >= TOP_K:
                break

            if s["priority"] < MIN_THRESHOLD:
                continue

            item = s["item"]
            topic = str(item.get("topic", "")).lower()

            if not topic or topic in used_topics:
                continue

            used_topics.add(topic)
            selected.append(s)

        # fallback
        if not selected and scored:
            selected = [scored[0]]

        # -------------------------
        # 4. ATTACH DECISION
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
