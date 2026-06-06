"""In-memory fakes implementing the application ports."""
from collections.abc import Callable

from src.application.ports import MessageBus, TelemetryLink, TelemetryRepository
from src.domain.dtos import ProcessedTelemetryDto


class FakeBus(MessageBus):
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []
        self.subscriptions: dict[str, Callable[[str, str], None]] = {}
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def publish(self, topic: str, payload: str, qos: int = 0) -> None:
        self.published.append((topic, payload))

    def subscribe(self, topic: str, on_message: Callable[[str, str], None]) -> None:
        self.subscriptions[topic] = on_message

    def loop_start(self) -> None:
        pass

    def loop_forever(self) -> None:
        pass

    def disconnect(self) -> None:
        self.connected = False

    def deliver(self, topic: str, payload: str) -> None:
        self.subscriptions[topic](topic, payload)


class FakeLink(TelemetryLink):
    def __init__(self) -> None:
        self.opened = False
        self.closed = False
        self.frames: list[str] = []

    def open(self) -> None:
        self.opened = True

    def send(self, payload: str) -> None:
        self.frames.append(payload)

    def close(self) -> None:
        self.closed = True


class FakeRepository(TelemetryRepository):
    def __init__(self, fail_on_insert: bool = False) -> None:
        self.sessions: list[str] = []
        self.inserted: list[ProcessedTelemetryDto] = []
        self.schema_ready = False
        self.fail_on_insert = fail_on_insert

    def init_schema(self) -> None:
        self.schema_ready = True

    def ensure_session(self, session_id: str, source: str = "carla") -> None:
        if session_id not in self.sessions:
            self.sessions.append(session_id)

    def insert(self, sample: ProcessedTelemetryDto) -> None:
        if self.fail_on_insert:
            raise RuntimeError("simulated DB failure")
        self.inserted.append(sample)

    def list_sessions(self) -> list[dict]:
        return [{"id": s} for s in self.sessions]

    def get_history(self, session_id: str, limit: int = 5000) -> list[dict]:
        return [s.model_dump() for s in self.inserted if s.session_id == session_id]

    def close(self) -> None:
        pass
