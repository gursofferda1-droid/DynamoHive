class AdaptiveFilter:

    def __init__(self):

        # başlangıç eşikleri
        self.base_threshold = 0.10
        self.max_threshold = 0.25

        # öğrenme hafızası
        self.history = []   # (priority, published)

        # dinamik eşik
        self.dynamic_threshold = self.base_threshold

    # -------------------------
    # FEEDBACK (ÖĞRENME)
    # -------------------------
    def update_feedback(self, items):

        for item in items:

            decision = item.get("decision", {})
            priority = decision.get("priority", 0)
            published = decision.get("publish", False)

            self.history.append((priority, published))

        # son 50 karar üzerinden öğren
        recent = self.history[-50:]

        if len(recent) < 10:
            return

        published_scores = [p for p, pub in recent if pub]
        rejected_scores = [p for p, pub in recent if not pub]

        if not published_scores or not rejected_scores:
            return

        avg_pub = sum(published_scores) / len(published_scores)
        avg_rej = sum(rejected_scores) / len(rejected_scores)

        # -------------------------
        # ADAPTIVE RULE
        # -------------------------
        # eğer çok düşükleri yayınlıyorsak sıkılaştır
        if avg_pub < avg_rej:
            self.dynamic_threshold = min(
                self.max_threshold,
                self.dynamic_threshold + 0.02
            )

        # eğer çok şey kaçırıyorsak gevşet
        else:
            self.dynamic_threshold = max(
                self.base_threshold,
                self.dynamic_threshold - 0.02
            )

    # -------------------------
    # FILTER CHECK
    # -------------------------
    def allow(self, priority):

        return priority >= self.dynamic_threshold

    # -------------------------
    # DEBUG
    # -------------------------
    def debug(self):

        return {
            "dynamic_threshold": round(self.dynamic_threshold, 3),
            "history_size": len(self.history)
        }
