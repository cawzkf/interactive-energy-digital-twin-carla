from src.application.acquisition_service import AcquisitionService, make_session_id
from src.exceptions import MarchForceError
from src.infra.config import AcquisitionConfig
from src.infra.logger import get_logger, setup_logging
from src.infra.messages import friendly
from src.infra.mqtt_client import MqttClient
from src.infra.sources import carla_source, sim_source

setup_logging()
logger = get_logger(__name__)


def main() -> None:
    source_name = AcquisitionConfig.SOURCE
    if source_name == "sim":
        source = sim_source()
    elif source_name == "carla":
        source = carla_source()
    else:
        raise ValueError(f"Unknown ACQ_SOURCE: {source_name!r} (use 'carla' or 'sim')")

    session_id = make_session_id()
    service = AcquisitionService(MqttClient(client_id=f"acquisition-{session_id}"), session_id)

    logger.info("acquisition_main", source=source_name, session=session_id)
    try:
        service.run(source)
    except KeyboardInterrupt:
        logger.warning("acquisition_interrupted", session=session_id)
    except MarchForceError as error:
        logger.error("acquisition_failed", reason=friendly(error))
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
