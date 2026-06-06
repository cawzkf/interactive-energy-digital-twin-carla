from src.application.ports import TelemetryLink
from src.exceptions import TelemetryLinkError
from src.infra.config import LoraConfig
from src.infra.logger import get_logger

logger = get_logger(__name__)


class LoggingLoRaLink(TelemetryLink):
    def open(self) -> None:
        logger.info("lora_link_log_mode")

    def send(self, payload: str) -> None:
        logger.info("lora_tx", bytes=len(payload.encode()), frame=payload)

    def close(self) -> None:
        pass


class SerialLoRaLink(TelemetryLink):
    def __init__(self, port: str = LoraConfig.PORT, baud: int = LoraConfig.BAUD) -> None:
        self.port = port
        self.baud = baud
        self._serial = None

    def open(self) -> None:
        try:
            import serial

            self._serial = serial.Serial(self.port, self.baud, timeout=1)
        except Exception as e:
            raise TelemetryLinkError(f"Could not open LoRa serial {self.port}: {e}") from e
        logger.info("lora_link_serial_open", port=self.port, baud=self.baud)

    def send(self, payload: str) -> None:
        if self._serial is None:
            raise TelemetryLinkError("LoRa serial link not open")
        self._serial.write((payload + "\n").encode())

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None


def build_link() -> TelemetryLink:
    """Select the link adapter from configuration."""
    if LoraConfig.LINK == "serial":
        return SerialLoRaLink()
    return LoggingLoRaLink()
