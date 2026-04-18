class DecisionEngine:

    def evaluate(self, items):

        output = []

        if not isinstance(items, list) or not items:
            return output

        scored = []

        # -------------------------
        # 1. SCORING
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
                # FINAL PRIORITY
                # -------------------------
                priority = (
                    (score * 0.30) +
                    (impact * 0.25) +
                    (confidence * 0.25) +
                    (urgency_score * 0.20)
                )

                # -------------------------
                # SOFT FILTER (FIXED)
                # -------------------------
                if score < 0.08 and impact < 0.15:
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

            except:
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
        MIN_THRESHOLD = 0.12   # 🔥 FIXED (was too strict)

        selected = []
        used_topics = set()

        for i, s in enumerate(scored):

            if len(selected) >= TOP_K:
                break

            topic = str(s["item"].get("topic", "")).lower()

            if topic in used_topics:
                continue

            # 🔥 threshold relaxed
            if s["priority"] >= MIN_THRESHOLD:
                selected.append(s)
                used_topics.add(topic)

        # -------------------------
        # 4. HARD FALLBACK (GUARANTEED OUTPUT)
        # -------------------------
        if not selected and scored:
            selected = scored[:2]   # 🔥 always produce something

        # -------------------------
        # 5. ATTACH DECISION
        # -------------------------
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
