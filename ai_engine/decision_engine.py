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
                score = float(item.get("score", 0))
                urgency = item.get("urgency", "low")

                urgency_map = {
                    "low": 0.3,
                    "medium": 0.6,
                    "high": 0.9
                }

                urgency_score = urgency_map.get(urgency, 0.3)

                # 🔥 SIMPLE + EFFECTIVE PRIORITY
                priority = (score * 0.7) + (urgency_score * 0.3)

                # 🔥 FILTER (çok agresif değil)
                if priority < 0.2:
                    continue

                scored.append({
                    "item": item,
                    "priority": priority
                })

            except:
                continue

        if not scored:
            return []

        # -------------------------
        # 2. SORT
        # -------------------------
        scored = sorted(scored, key=lambda x: x["priority"], reverse=True)

        # -------------------------
        # 3. SELECT (🔥 DAHA FAZLA İÇERİK)
        # -------------------------
        TOP_K = 10   # 🔥 arttırdık
        selected = scored[:TOP_K]

        # -------------------------
        # 4. ATTACH DECISION
        # -------------------------
        for idx, s in enumerate(scored):

            item = s["item"]

            publish = s in selected

            item["decision"] = {
                "publish": publish,
                "priority": round(s["priority"], 3),
                "rank": idx + 1
            }

            output.append(item)

        return output
