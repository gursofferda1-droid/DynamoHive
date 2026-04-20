import time

from backend.logger import logger


def predict_trend(intel):

    topic = str(intel.get("topic", "")).lower()
    score = float(intel.get("score", 0.5))
    insight = str(intel.get("insight", "")).lower()

    trend = "neutral"
    risk = "low"
    horizon = "short-term"

    # -------------------------
    # TREND
    # -------------------------
    if score >= 0.75:
        trend = "explosive"
    elif score >= 0.45:
        trend = "rising"
    elif score >= 0.25:
        trend = "emerging"

    # -------------------------
    # TOPIC ANALYSIS
    # -------------------------
    if any(x in topic for x in ["war", "attack", "missile", "conflict", "strike"]):
        risk = "high"
        horizon = "immediate"

    elif any(x in topic for x in ["collapse", "crisis", "default", "recession"]):
        risk = "medium"
        horizon = "mid-term"

    elif any(x in topic for x in ["ai", "ipo", "expansion", "chip", "startup"]):
        trend = "growth"
        horizon = "mid-term"

    # -------------------------
    # INSIGHT BOOST
    # -------------------------
    if any(x in insight for x in ["geopolitical", "power shift", "escalation"]):
        risk = "high"

    if any(x in insight for x in ["technology", "ai", "automation"]):
        if trend == "neutral":
            trend = "strategic"

    # -------------------------
    # CONFIDENCE
    # -------------------------
    confidence = max(0.1, min(score, 1.0))

    return {
        "trend": trend,
        "risk": risk,
        "horizon": horizon,
        "confidence": round(confidence, 2),
        "timestamp": int(time.time())
    }


class PredictionEngine:

    def forecast(self, signal, context):

        try:
            topic = signal.get("topic") or signal.get("title") or ""

            intel = {
                "topic": topic,
                "score": signal.get("score", 0.5),
                "insight": context.get("insight", "")
            }

            result = predict_trend(intel)

            result["impact_score"] = result.get("confidence", 0.5)

            risk = result.get("risk", "low")

            urgency_map = {
                "low": "low",
                "medium": "medium",
                "high": "high"
            }

            result["urgency"] = urgency_map.get(risk, "low")

            return result

        except Exception as e:
            logger.warning(f"[PREDICTION ERROR] {e}")

            return {
                "trend": "neutral",
                "risk": "low",
                "horizon": "short-term",
                "confidence": 0.5,
                "impact_score": 0.5,
                "urgency": "low"
            }
