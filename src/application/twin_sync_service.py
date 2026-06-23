from src.application.ports import MessageBus
from src.application.twin_service import TwinService
from src.domain.aas_model import TELEMETRY_MODEL
from src.domain.dtos import ProcessedTelemetryDto
from src.infra.config import MqttConfig
from src.infra.logger import get_logger

logger = get_logger(__name__)


class TwinSyncService:
    def __init__(self, bus: MessageBus, twin: TwinService) -> None:
        self._bus = bus
        self._twin = twin

    def _publish_aas_mqtt(self, sample: ProcessedTelemetryDto) -> None:
        for submodel, variables in TELEMETRY_MODEL.items():
            for id_short, field, scale in variables:
                value = getattr(sample, field) * scale
                topic = f"{MqttConfig.TOPIC_AAS}/{submodel}/{id_short}"
                self._bus.publish(topic, str(round(value, 4)))
        logger.debug("aas_mqtt_published", session=sample.session_id)

    def process_message(self, topic: str, payload: str) -> None:
        sample = ProcessedTelemetryDto.model_validate_json(payload)
        self._twin.sync_processed(sample)
        self._publish_aas_mqtt(sample)

    def run(self) -> None:
        self._bus.connect()
        self._bus.subscribe(MqttConfig.TOPIC_PROCESSED, self.process_message)
        logger.info("twin_sync_start", topic=MqttConfig.TOPIC_PROCESSED)
        self._bus.loop_forever()
