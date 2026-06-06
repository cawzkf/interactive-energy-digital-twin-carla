from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator

from src.domain.dtos import ProcessedTelemetryDto, UpdateRequestDto

TelemetrySource = Iterator[UpdateRequestDto]


class MessageBus(ABC):
    """Logical bus used to decouple services (implemented by MQTT)."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def publish(self, topic: str, payload: str, qos: int = 0) -> None: ...

    @abstractmethod
    def subscribe(self, topic: str, on_message: Callable[[str, str], None]) -> None: ...

    @abstractmethod
    def loop_start(self) -> None: ...

    @abstractmethod
    def loop_forever(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...


class TelemetryLink(ABC):
    """External one-way telemetry link (e.g. LoRa to the box)."""

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def send(self, payload: str) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class TelemetryRepository(ABC):
    """Persistence of processed telemetry organized by test session."""

    @abstractmethod
    def init_schema(self) -> None: ...

    @abstractmethod
    def ensure_session(self, session_id: str, source: str = "carla") -> None: ...

    @abstractmethod
    def insert(self, sample: ProcessedTelemetryDto) -> None: ...

    @abstractmethod
    def list_sessions(self) -> list[dict]: ...

    @abstractmethod
    def get_history(self, session_id: str, limit: int = 5000) -> list[dict]: ...

    @abstractmethod
    def close(self) -> None: ...
