import os
from enum import StrEnum
from pathlib import Path

from dotenv import load_dotenv

APP_ENV = os.getenv("APP_ENV", "dev")

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
_ENV_FILE = _CONFIG_DIR / f".env.{APP_ENV}"
load_dotenv(_ENV_FILE, override=False)


def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(
            f"Missing required env var {name!r} for APP_ENV={APP_ENV!r}. "
            f"Set it in {_ENV_FILE} or in the process environment."
        )
    return value


class SourceType(StrEnum):
    CARLA = "carla"
    SIM = "sim"


class MqttConfig:
    HOST: str = os.getenv("MQTT_HOST", "localhost")
    PORT: int = int(os.getenv("MQTT_PORT", "1883"))
    TOPIC_RAW: str = os.getenv("MQTT_TOPIC_RAW", "marchforce/telemetry/raw")
    TOPIC_PROCESSED: str = os.getenv(
        "MQTT_TOPIC_PROCESSED", "marchforce/telemetry/processed"
    )
    TOPIC_CONTROL: str = os.getenv("MQTT_TOPIC_CONTROL", "marchforce/control")
    TOPIC_CONFIG: str = os.getenv("MQTT_TOPIC_CONFIG", "marchforce/config")
    KEEPALIVE: int = int(os.getenv("MQTT_KEEPALIVE", "60"))


class DbConfig:
    HOST: str = os.getenv("DB_HOST", "localhost")
    PORT: int = int(os.getenv("DB_PORT", "5432"))
    NAME: str = os.getenv("DB_NAME", "telemetry")
    USER: str = os.getenv("DB_USER", "")
    PASSWORD: str = os.getenv("DB_PASSWORD", "")

    @classmethod
    def dsn(cls) -> str:
        full = os.getenv("TELEMETRY_DSN")
        if full:
            return full
        user = cls.USER or _require("DB_USER")
        password = cls.PASSWORD or _require("DB_PASSWORD")
        return f"postgresql://{user}:{password}@{cls.HOST}:{cls.PORT}/{cls.NAME}"


class AcquisitionConfig:
    SOURCE: str = os.getenv("ACQ_SOURCE", SourceType.CARLA.value)
    NOMINAL_DC_VOLTAGE: float = float(os.getenv("NOMINAL_DC_VOLTAGE", "48.0"))
    CARLA_HOST: str = os.getenv("CARLA_HOST", "10.255.255.254")
    CARLA_PORT: int = int(os.getenv("CARLA_PORT", "2000"))


class ApiConfig:
    HOST: str = os.getenv("API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("API_PORT", "8000"))


class TwinConfig:
    BASYX_URL: str = os.getenv("BASYX_URL", "http://localhost:8081")


class OpcuaConfig:
    BIND_HOST: str = os.getenv("OPCUA_BIND_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("OPCUA_PORT", "4840"))
    PATH: str = os.getenv("OPCUA_PATH", "/marchforce/")
    NAMESPACE: str = os.getenv("OPCUA_NAMESPACE", "http://marchforce.telemetry")
    SERVER_NAME: str = os.getenv("OPCUA_SERVER_NAME", "MarchForce Telemetry")
    SHELL_NAME: str = os.getenv("OPCUA_SHELL_NAME", "VehicleEnergyDigitalTwin")
    UPDATE_INTERVAL: float = float(os.getenv("OPCUA_UPDATE_INTERVAL", "0.2"))

    @classmethod
    def endpoint(cls) -> str:
        return f"opc.tcp://{cls.BIND_HOST}:{cls.PORT}{cls.PATH}"


class VehicleConfig:
    MASS_VEHICLE: float = float(os.getenv("VEHICLE_MASS", "60"))
    MASS_DRIVER: float = float(os.getenv("DRIVER_MASS", "50"))
    TOTAL_MASS: float = MASS_VEHICLE + MASS_DRIVER
    DRAG_COEFFICIENT: float = float(os.getenv("VEHICLE_DRAG", "0.10"))
    FRONTAL_AREA: float = float(os.getenv("VEHICLE_FRONTAL_AREA", "0.5"))
    ROLLING_RESISTANCE: float = float(os.getenv("VEHICLE_ROLLING", "0.002"))
    BATTERY_CAPACITY_J: float = float(os.getenv("BATTERY_CAPACITY_J", "5000000"))


class LoraConfig:
    LINK: str = os.getenv("LORA_LINK", "log")
    PORT: str = os.getenv("LORA_PORT", "/dev/ttyUSB0")
    BAUD: int = int(os.getenv("LORA_BAUD", "9600"))
    FIELDS: list[str] = [
        f.strip()
        for f in os.getenv("LORA_FIELDS", "velocity,soc,power,vdc,idc").split(",")
        if f.strip()
    ]
    MAX_BYTES: int = int(os.getenv("LORA_MAX_BYTES", "200"))
    MIN_INTERVAL: float = float(os.getenv("LORA_MIN_INTERVAL", "1.0"))
