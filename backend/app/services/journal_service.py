from datetime import datetime, timezone


class JournalService:
    """In-memory journal placeholder.

    In the next iteration this should write to Postgres tables.
    """

    def __init__(self):
        self.events: list[dict] = []

    def log_blocked_signal(self, signal: dict, prediction: dict, reason: str) -> dict:
        event = {
            'type': 'blocked_signal',
            'reason': reason,
            'signal': signal,
            'prediction': prediction,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        self.events.append(event)
        return event

    def log_executed_paper_order(self, order: dict, signal: dict, prediction: dict) -> dict:
        event = {
            'type': 'paper_order_executed',
            'order': order,
            'signal': signal,
            'prediction': prediction,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        self.events.append(event)
        return event

    def list_events(self) -> list[dict]:
        return self.events[-100:]


journal_service = JournalService()
