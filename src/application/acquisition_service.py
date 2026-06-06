import time

from src.application.ports import MessageBus, TelemetrySource
from src.domain.dtos import RawTelemetryDto
from src.infra.config import MqttConfig
from src.infra.logger import get_logger

logger = get_logger(__name__)


def make_session_id(prefix: str = "sess") -> str:
    return f"{prefix}-{time.strftime('%Y%m%d-%H%M%S')}"


class AcquisitionService:
    def __init__(self, mqtt_client: MessageBus, session_id: str) -> None:
        self._mqtt = mqtt_client
        self.session_id = session_id

    def run(self, source: TelemetrySource) -> None:
        self._mqtt.connect()
        self._mqtt.loop_start()
        logger.info("acquisition_start", session=self.session_id)

        count = 0
        for state in source:
            raw = RawTelemetryDto(
                session_id=self.session_id,
                timestamp=time.time(),
                velocity=state.velocity,
                acceleration=state.acceleration,
                dt=state.dt,
                x=state.x,
                y=state.y,
            )
            self._mqtt.publish(MqttConfig.TOPIC_RAW, raw.model_dump_json())
            count += 1
            if count % 50 == 0:
                logger.info(
                    "acquisition_progress",
                    session=self.session_id,
                    samples=count,
                    velocity=round(state.velocity, 2),
                )

        logger.info("acquisition_end", session=self.session_id, samples=count)
        self._mqtt.disconnect()
