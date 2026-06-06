import asyncio

from src.application.opcua_service import OpcuaService
from src.infra.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def main() -> None:
    try:
        asyncio.run(OpcuaService().run())
    except KeyboardInterrupt:
        logger.warning("opcua_interrupted")


if __name__ == "__main__":
    main()
