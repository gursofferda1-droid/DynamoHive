from backend.storage import get_feedback, get_state, set_state


class DecisionEngine:

    def __init__(self):
        # 🔥 platform memory injection
        self.feedback_history = get_feedback(200)
        self.global_state = get_state("decision_state") or {}

    def evaluate(self, items):

        output = []

        if not isinstance(items, list) or not items:
            return output

        scored = []

        # -------------------------
        # 0. MEMORY WEIGHT ADAPTATION
        # -------------------------
        topic_success_map = self._build_topic_success_map()

        # -------------------------
        # 1. SCORING (ENHANCED)
        # -------------------------
        for item in items:

            try:
                signal = item.get("signal", {})
                prediction = item.get("prediction", {})
                reasoning = item.get("reasoning", {})

                score = signal.get("score", 0)
                impact = prediction.get("impact_score", 0.5)

                confidence = reasoning.get("confidence", 0.5) if isinstance(reasoning, dict) else 0.5
                urgency = item.get("urgency", "low")

                urgency_map = {
                    "low": 0.3,
                    "medium": 0.6,
                    "high": 0.9
                }

                urgency_score = urgency_map.get(urgency, 0.3)

                topic = str(item.get("topic", "")).lower()

                # 🔥 MEMORY BOOST (platform farkı burada)
                memory_boost = topic_success_map.get(topic, 0)

                # 🔥 FINAL PRIORITY (adaptive)
                priority = (
                    (score * 0.25) +
                    (impact * 0.25) +
                    (confidence * 0.20) +
                    (urgency_score * 0.20) +
                    (memory_boost * 0.10)
                )

                # 🔥 dynamic filter (hard rule yerine adaptive)
                min_dynamic_score = self.global_state.get("min_score", 0.15)

                if score < min_dynamic_score and impact < 0.25:
                    continue

                scored.append({
                    "item": item,
                    "priority": priority,
                    "meta": {
                        "score": score,
                        "impact": impact,
                        "confidence": confidence,
                        "urgency": urgency,
                        "memory_boost": memory_boost
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
        # 3. SELECTION (ADAPTIVE TOP-K)
        # -------------------------
        top_k = self.global_state.get("top_k", 5)
        min_threshold = self.global_state.get("min_threshold", 0.25)

        selected = []
        used_topics = set()

        for s in scored:

            if len(selected) >= top_k:
                break

            if s["priority"] < min_threshold:
                continue

            topic = str(s["item"].get("topic", "")).lower()

            if topic in used_topics:
                continue

            used_topics.add(topic)
            selected.append(s)

        # fallback
        if not selected and scored:
            selected = [scored[0]]

        # -------------------------
        # 4. ATTACH DECISION
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

        # -------------------------
        # 5. PLATFORM STATE UPDATE (KRİTİK EK)
        # -------------------------
        self._update_state(scored, selected)

        return output

    # -------------------------
    # PLATFORM MEMORY BUILD
    # -------------------------
    def _build_topic_success_map(self):

        topic_map = {}

        for f in self.feedback_history:

            try:
                topic = str(f.get("signal_topic", "")).lower()
                engagement = float(f.get("engagement_score", 0))

                if not topic:
                    continue

                if topic not in topic_map:
                    topic_map[topic] = []

                topic_map[topic].append(engagement)

            except:
                continue

        # average success
        return {
            k: sum(v) / len(v) for k, v in topic_map.items() if v
        }

    # -------------------------
    # STATE UPDATE LOOP
    # -------------------------
    def _update_state(self, scored, selected):

        try:
            success_rate = len(selected) / max(len(scored), 1)

            current = self.global_state or {}

            # adaptive tuning
            current["last_success_rate"] = success_rate

            if success_rate < 0.2:
                current["min_threshold"] = min(
                    current.get("min_threshold", 0.25) + 0.05,
                    0.6
                )
            else:
                current["min_threshold"] = max(
                    current.get("min_threshold", 0.25) - 0.01,
                    0.1
                )

            set_state("decision_state", current)

        except:
            pass
