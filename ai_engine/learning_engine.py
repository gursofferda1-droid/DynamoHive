class LearningEngine:

    def __init__(self):
        self.history = []

        # başlangıç ağırlıkları
        self.weights = {
            "score": 0.30,
            "impact": 0.25,
            "confidence": 0.25,
            "urgency": 0.20
        }

    def record(self, item, outcome_score=0.5):

        self.history.append({
            "item": item,
            "outcome": outcome_score
        })

        # son 100 kayıtla adapt
        self.history = self.history[-100:]
        self._adapt()

    def _adapt(self):

        if len(self.history) < 10:
            return

        good = [h for h in self.history if h["outcome"] > 0.6]

        if len(good) < 3:
            return

        # basit adaptasyon
        self.weights["confidence"] += 0.01
        self.weights["score"] -= 0.005
        self.weights["urgency"] += 0.005

        # clamp
        for k in self.weights:
            self.weights[k] = max(0.1, min(0.6, self.weights[k]))
