from src.application.processing_service import ProcessingService
from src.exceptions import MarchForceError
from src.infra.logger import get_logger, setup_logging
from src.infra.messages import friendly
from src.infra.mqtt_client import MqttClient
from src.infra.timescale_repository import TimescaleRepository

setup_logging()
logger = get_logger(__name__)


def main() -> None:
    repository = None
    try:
        repository = TimescaleRepository()
        service = ProcessingService(MqttClient(client_id="processing"), repository)
        service.run()
    except KeyboardInterrupt:
        logger.warning("processing_interrupted")
    except MarchForceError as error:
        logger.error("processing_failed", reason=friendly(error))
        raise SystemExit(1) from error
    finally:
        if repository is not None:
            repository.close()


if __name__ == "__main__":
    main()
