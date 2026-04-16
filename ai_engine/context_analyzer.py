class ContextAnalyzer:

    def build(self, signal, memory):
        try:
            topic = str(signal.get("topic", "")).strip()
            history = memory.get("history", [])

            previous_topics = []

            for item in history:
                if isinstance(item, dict):
                    old_topic = str(item.get("topic", "")).strip().lower()
                    if old_topic:
                        previous_topics.append(old_topic)

            normalized_topic = topic.lower()

            repeated = normalized_topic in previous_topics

            if repeated:
                insight = "recurring_topic"
            elif history:
                insight = "new_topic_with_history"
            else:
                insight = "first_topic"

            return {
                "actors": ["state actors"],
                "region": "global",
                "topic": topic,
                "history": history,
                "insight": insight
            }

        except Exception:
            return {
                "actors": [],
                "region": "global",
                "topic": "",
                "history": [],
                "insight": "context_error"
            }
