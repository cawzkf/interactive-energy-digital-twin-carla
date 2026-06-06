from collections.abc import Callable

import paho.mqtt.client as mqtt

from src.application.ports import MessageBus
from src.exceptions import MessageBusError
from src.infra.config import MqttConfig
from src.infra.logger import get_logger

logger = get_logger(__name__)


class MqttClient(MessageBus):
    def __init__(
        self,
        client_id: str,
        host: str = MqttConfig.HOST,
        port: int = MqttConfig.PORT,
    ) -> None:
        self.host = host
        self.port = port
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._subscriptions: list[str] = []

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code == 0:
            logger.info("mqtt_connected", host=self.host, port=self.port)
            for topic in self._subscriptions:
                client.subscribe(topic)
        else:
            logger.error("mqtt_connect_failed", reason=str(reason_code))

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        logger.warning("mqtt_disconnected", reason=str(reason_code))

    def connect(self) -> None:
        try:
            self._client.connect(self.host, self.port, MqttConfig.KEEPALIVE)
        except OSError as e:
            raise MessageBusError(
                f"Could not connect to MQTT broker at {self.host}:{self.port}: {e}"
            ) from e

    def publish(self, topic: str, payload: str, qos: int = 0) -> None:
        self._client.publish(topic, payload, qos=qos)

    def subscribe(self, topic: str, on_message: Callable[[str, str], None]) -> None:
        self._subscriptions.append(topic)

        def _handler(client, userdata, msg) -> None:
            try:
                on_message(msg.topic, msg.payload.decode())
            except Exception as e:
                logger.error("mqtt_message_handler_error", error=str(e))

        self._client.message_callback_add(topic, _handler)
        self._client.subscribe(topic)

    def loop_forever(self) -> None:
        self._client.loop_forever()

    def loop_start(self) -> None:
        self._client.loop_start()

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
