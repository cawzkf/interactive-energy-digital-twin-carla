from src.application.lora_service import LoraService
from src.exceptions import MarchForceError
from src.infra.logger import get_logger, setup_logging
from src.infra.lora_link import build_link
from src.infra.messages import friendly
from src.infra.mqtt_client import MqttClient

setup_logging()
logger = get_logger(__name__)


def main() -> None:
    service = LoraService(MqttClient(client_id="lora"), build_link())
    try:
        service.run()
    except KeyboardInterrupt:
        logger.warning("lora_interrupted")
    except MarchForceError as error:
        logger.error("lora_failed", reason=friendly(error))
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
