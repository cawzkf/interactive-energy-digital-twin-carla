import json
import time
from collections.abc import Callable

from src.application.ports import MessageBus, TelemetryLink
from src.domain.diagnostics import Severity
from src.domain.dtos import ProcessedTelemetryDto
from src.infra.config import LoraConfig, MqttConfig
from src.infra.logger import get_logger

logger = get_logger(__name__)


class LoraService:
    def __init__(
        self,
        bus: MessageBus,
        link: TelemetryLink,
        fields: list[str] | None = None,
        min_interval: float = LoraConfig.MIN_INTERVAL,
        max_bytes: int = LoraConfig.MAX_BYTES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._bus = bus
        self._link = link
        self._fields = fields if fields is not None else LoraConfig.FIELDS
        self._min_interval = min_interval
        self._max_bytes = max_bytes
        self._clock = clock
        self._last_sent: float | None = None
        self.sent_count = 0

    def _worst_alert(self, sample: ProcessedTelemetryDto) -> str | None:
        errors = [a for a in sample.alerts if a.severity == Severity.ERROR]
        return errors[0].code.value if errors else None

    def _build_frame(self, sample: ProcessedTelemetryDto) -> str:
        frame: dict[str, object] = {"sid": sample.session_id, "t": round(sample.timestamp, 1)}
        for field in self._fields:
            value = getattr(sample, field, None)
            if isinstance(value, float):
                value = round(value, 3)
            frame[field] = value
        alert = self._worst_alert(sample)
        if alert is not None:
            frame["alert"] = alert
        return json.dumps(frame, separators=(",", ":"))

    def process_message(self, topic: str, payload: str) -> None:
        now = self._clock()
        if self._last_sent is not None and (now - self._last_sent) < self._min_interval:
            return

        sample = ProcessedTelemetryDto.model_validate_json(payload)
        frame = self._build_frame(sample)

        size = len(frame.encode())
        if size > self._max_bytes:
            logger.warning("lora_frame_oversize", bytes=size, limit=self._max_bytes)
            return

        self._link.send(frame)
        self._last_sent = now
        self.sent_count += 1

    def run(self) -> None:
        self._link.open()
        self._bus.connect()
        self._bus.subscribe(MqttConfig.TOPIC_PROCESSED, self.process_message)
        logger.info("lora_service_start", fields=self._fields, interval=self._min_interval)
        try:
            self._bus.loop_forever()
        finally:
            self._link.close()
