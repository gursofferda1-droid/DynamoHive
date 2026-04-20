from backend.logger import logger


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

                score = float(signal.get("score", 0))
                impact = float(prediction.get("impact_score", 0.5))

                confidence = 0.5
                if isinstance(reasoning, dict):
                    confidence = float(reasoning.get("confidence", 0.5))

                urgency = str(item.get("urgency", "low")).lower()

                urgency_map = {
                    "low": 0.3,
                    "medium": 0.6,
                    "high": 0.9
                }

                urgency_score = urgency_map.get(urgency, 0.3)

                priority = (
                    (score * 0.30) +
                    (impact * 0.25) +
                    (confidence * 0.20) +
                    (urgency_score * 0.25)
                )

                # hard filter
                if score < 0.15 and impact < 0.25:
                    item["decision"] = {
                        "publish": False,
                        "priority": round(priority, 3),
                        "reason": "low_signal"
                    }
                    output.append(item)
                    continue

                scored.append({
                    "item": item,
                    "priority": priority,
                    "meta": {
                        "score": round(score, 3),
                        "impact": round(impact, 3),
                        "confidence": round(confidence, 3),
                        "urgency": urgency
                    }
                })

            except Exception as e:
                logger.warning(f"[DECISION ERROR] {e}")
                continue

        if not scored:
            return output

        # -------------------------
        # 2. SORT
        # -------------------------
        scored = sorted(scored, key=lambda x: x["priority"], reverse=True)

        # -------------------------
        # 3. SELECTION
        # -------------------------
        TOP_K = 5
        MIN_THRESHOLD = 0.25

        selected_topics = set()

        for idx, s in enumerate(scored):
            item = s["item"]
            topic = str(item.get("topic", "")).strip().lower()

            publish = False
            reason = "below_threshold"

            if s["priority"] < MIN_THRESHOLD:
                reason = "below_threshold"

            elif topic in selected_topics:
                reason = "duplicate_topic"

            elif len(selected_topics) >= TOP_K:
                reason = "top_k_limit"

            else:
                publish = True
                reason = "selected"
                selected_topics.add(topic)

            item["decision"] = {
                "publish": publish,
                "priority": round(s["priority"], 3),
                "rank": idx + 1,
                "reason": reason,
                **s["meta"]
            }

            output.append(item)

        # fallback → en az 1 içerik
        if not any(x.get("decision", {}).get("publish") for x in output):
            best = output[0]
            best["decision"]["publish"] = True
            best["decision"]["reason"] = "fallback_selected"

        logger.info(
            f"[DECISION] total={len(items)} scored={len(scored)} "
            f"published={sum(1 for x in output if x.get('decision', {}).get('publish'))}"
        )

        return output
