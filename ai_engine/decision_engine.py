class DecisionEngine:

    def evaluate(self, items):
        output = []

        if not isinstance(items, list) or not items:
            return output

        scored = []

        # ---------------------------------
        # 1. PRIORITY SCORING
        # ---------------------------------
        for item in items:
            try:
                signal = item.get("signal", {})
                prediction = item.get("prediction", {})
                reasoning = item.get("reasoning", {})

                score = float(signal.get("score", item.get("score", 0)))
                impact = float(prediction.get("impact_score", 0.5))

                if isinstance(reasoning, dict):
                    confidence = float(reasoning.get("confidence", 0.5))
                else:
                    confidence = 0.5

                urgency = str(item.get("urgency", "low")).lower()

                urgency_map = {
                    "low": 0.30,
                    "medium": 0.60,
                    "high": 0.90
                }

                urgency_score = urgency_map.get(urgency, 0.30)

                priority = (
                    (score * 0.30) +
                    (impact * 0.25) +
                    (confidence * 0.20) +
                    (urgency_score * 0.25)
                )

                # düşük kalite spam filtre
                if score < 0.10 and impact < 0.20 and confidence < 0.20:
                    continue

                scored.append({
                    "item": item,
                    "priority": round(priority, 4),
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

        # ---------------------------------
        # 2. SORT
        # ---------------------------------
        scored.sort(key=lambda x: x["priority"], reverse=True)

        # ---------------------------------
        # 3. DYNAMIC THRESHOLD
        # ---------------------------------
        TOP_K = 5

        top_priority = scored[0]["priority"]
        dynamic_threshold = max(0.22, top_priority * 0.55)

        selected = []
        used_topics = set()

        for s in scored:
            if len(selected) >= TOP_K:
                break

            topic = str(s["item"].get("topic", "")).strip().lower()

            if not topic:
                continue

            if topic in used_topics:
                continue

            if s["priority"] < dynamic_threshold:
                continue

            used_topics.add(topic)
            selected.append(s)

        # en az 1 yayın
        if not selected:
            selected = [scored[0]]

        selected_ids = {id(s) for s in selected}

        # ---------------------------------
        # 4. ATTACH DECISION
        # ---------------------------------
        for idx, s in enumerate(scored):
            item = s["item"]

            publish = id(s) in selected_ids

            item["decision"] = {
                "publish": publish,
                "priority": round(s["priority"], 3),
                "rank": idx + 1,
                **s["meta"]
            }

            output.append(item)

        return output
