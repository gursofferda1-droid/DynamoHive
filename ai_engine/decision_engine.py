class DecisionEngine:

    def evaluate(self, items):

        if not items:
            return []

        scored = []

        for item in items:

            try:
                signal = item.get("signal", {})
                prediction = item.get("prediction", {})

                score = signal.get("score", 0)
                impact = prediction.get("impact_score", 0.5)
                confidence = item.get("reasoning", {}).get("confidence", 0.5)

                urgency_map = {"low": 0.3, "medium": 0.6, "high": 0.9}
                urgency = urgency_map.get(item.get("urgency", "low"), 0.3)

                priority = (
                    score * 0.30 +
                    impact * 0.25 +
                    confidence * 0.25 +
                    urgency * 0.20
                )

                if score < 0.15 and impact < 0.25:
                    continue

                scored.append({
                    "item": item,
                    "priority": priority,
                    "meta": {
                        "score": score,
                        "impact": impact,
                        "confidence": confidence,
                        "urgency": item.get("urgency", "low")
                    }
                })

            except:
                continue

        scored.sort(key=lambda x: x["priority"], reverse=True)

        selected = []
        used = set()

        for s in scored:

            if len(selected) >= 5:
                break

            topic = str(s["item"].get("topic", "")).lower()

            if topic in used:
                continue

            used.add(topic)
            selected.append(s)

        output = []

        for i, s in enumerate(scored):

            item = s["item"]
            item["decision"] = {
                "publish": s in selected,
                "priority": round(s["priority"], 3),
                "rank": i + 1,
                **s["meta"]
            }

            output.append(item)

        return output
