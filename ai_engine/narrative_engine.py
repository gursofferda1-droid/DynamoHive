from backend.logger import logger


def generate_narrative(intel):

    try:
        if not isinstance(intel, dict):
            intel = {}

        topic = str(intel.get("topic") or "").strip()
        insight = str(intel.get("insight") or "").lower()

        actors = intel.get("actors")
        if not isinstance(actors, list):
            actors = []

        region = str(intel.get("region") or "global")
        urgency = str(intel.get("urgency") or "low").lower()

        decision = intel.get("decision", {})
        priority = decision.get("priority", 0)

        if urgency not in ["low", "medium", "high"]:
            urgency = "low"

        what = topic if topic else "Unknown signal"

        # -------------------------
        # CATEGORY
        # -------------------------
        if any(k in insight for k in ["geopolitical", "conflict", "war"]):
            category = "geopolitical"

        elif any(k in insight for k in ["ai", "technology", "technological"]):
            category = "technology"

        elif any(k in insight for k in ["economic", "finance", "market"]):
            category = "economic"

        elif any(k in insight for k in ["social", "society", "protest"]):
            category = "social"

        else:
            category = "general"

        # -------------------------
        # WHY
        # -------------------------
        why_map = {
            "geopolitical": "This reflects shifting geopolitical pressure and strategic positioning.",
            "technology": "This signals acceleration in technological competition and capability shifts.",
            "economic": "This indicates movement in economic influence or capital flows.",
            "social": "This reflects deeper social instability or public pressure.",
            "general": "This is an emerging signal gaining structural relevance."
        }

        why = why_map.get(category)

        # -------------------------
        # IMPACT
        # -------------------------
        if urgency == "high" or priority >= 0.7:
            impact = "High probability of escalation or broader systemic consequences."

        elif urgency == "medium" or priority >= 0.4:
            impact = "Likely to influence regional or sector-level dynamics."

        else:
            impact = "Currently limited, but worth monitoring for further change."

        # -------------------------
        # NEXT
        # -------------------------
        next_map = {
            "geopolitical": "Watch for escalation, alliances, sanctions, or counter-actions.",
            "technology": "Expect rapid iteration, competitive response, and regulatory pressure.",
            "economic": "Monitor capital movement, pricing shifts, and institutional reactions.",
            "social": "Track sentiment shifts, mobilization patterns, and policy response.",
            "general": "Track signal frequency and cross-domain spread."
        }

        nxt = next_map.get(category)

        title = topic[:120] if topic else "Signal"

        content = (
            f"{what}\n\n"
            f"Why it matters:\n{why}\n\n"
            f"Impact:\n{impact}\n\n"
            f"What to watch:\n{nxt}"
        )

        return {
            "title": title,
            "content": content,
            "meta": {
                "actors": actors,
                "region": region,
                "urgency": urgency,
                "category": category,
                "priority": priority
            }
        }

    except Exception as e:
        logger.warning(f"[NARRATIVE ERROR] {e}")

        topic = str(intel.get("topic") or "fallback")

        return {
            "title": topic[:120],
            "content": topic,
            "meta": {
                "actors": [],
                "region": "global",
                "urgency": "low",
                "category": "general",
                "priority": 0
            }
        }
