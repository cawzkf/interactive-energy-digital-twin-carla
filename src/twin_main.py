from src.application.twin_service import TwinService
from src.application.twin_sync_service import TwinSyncService
from src.exceptions import MarchForceError
from src.infra.config import TwinConfig
from src.infra.logger import get_logger, setup_logging
from src.infra.messages import friendly
from src.infra.mqtt_client import MqttClient

setup_logging()
logger = get_logger(__name__)


def main() -> None:
    twin = TwinService(TwinConfig.BASYX_URL)
    if not twin.check_connection():
        logger.warning("basyx_unreachable", url=TwinConfig.BASYX_URL)

    service = TwinSyncService(MqttClient(client_id="twin-sync"), twin)
    try:
        service.run()
    except KeyboardInterrupt:
        logger.warning("twin_sync_interrupted")
    except MarchForceError as error:
        logger.error("twin_sync_failed", reason=friendly(error))
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
