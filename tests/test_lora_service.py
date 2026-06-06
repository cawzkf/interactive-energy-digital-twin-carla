"""Unit tests for the LoRa service, structured as Arrange-Act-Assert."""
import json

from src.application.lora_service import LoraService
from src.domain.diagnostics import Alert, AlertCode, Severity
from src.domain.dtos import ProcessedTelemetryDto
from src.infra.config import MqttConfig
from tests.fakes import FakeBus, FakeLink


class _Clock:
    """Deterministic clock so throttling is tested without sleeping."""
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _processed(timestamp=1700000000.0, alerts=None, **overrides):
    base = dict(
        session_id="sess", timestamp=timestamp, velocity=12.0, acceleration=0.0,
        vdc=48.0, idc=5.0, power=600.0, energy=10.0, soc=0.8,
        distance=1.0, avg_power=600.0, specific_consumption=0.0, autonomy=100.0,
        alerts=alerts or [],
    )
    base.update(overrides)
    return ProcessedTelemetryDto(**base).model_dump_json()


class TestFrameContent:
    def test_frame_contains_only_selected_fields_plus_metadata(self):
        # Arrange
        bus, link = FakeBus(), FakeLink()
        service = LoraService(bus, link, fields=["velocity", "soc"], clock=_Clock())

        # Act
        service.process_message(MqttConfig.TOPIC_PROCESSED, _processed())

        # Assert
        frame = json.loads(link.frames[0])
        assert set(frame.keys()) == {"sid", "t", "velocity", "soc"}
        assert frame["velocity"] == 12.0
        assert frame["soc"] == 0.8

    def test_critical_alert_is_included(self):
        # Arrange
        bus, link = FakeBus(), FakeLink()
        service = LoraService(bus, link, fields=["soc"], clock=_Clock())
        alerts = [Alert.of(AlertCode.SOC_CRITICAL, Severity.ERROR, 4.0)]

        # Act
        service.process_message(MqttConfig.TOPIC_PROCESSED, _processed(alerts=alerts))

        # Assert
        frame = json.loads(link.frames[0])
        assert frame["alert"] == AlertCode.SOC_CRITICAL.value

    def test_warning_alert_is_not_forwarded(self):
        # Arrange
        bus, link = FakeBus(), FakeLink()
        service = LoraService(bus, link, fields=["soc"], clock=_Clock())
        alerts = [Alert.of(AlertCode.SOC_LOW, Severity.WARNING, 15.0)]

        # Act
        service.process_message(MqttConfig.TOPIC_PROCESSED, _processed(alerts=alerts))

        # Assert — only critical (error) alerts go to the box
        frame = json.loads(link.frames[0])
        assert "alert" not in frame


class TestThrottling:
    def test_drops_samples_within_min_interval(self):
        # Arrange
        clock = _Clock()
        bus, link = FakeBus(), FakeLink()
        service = LoraService(bus, link, fields=["soc"], min_interval=1.0, clock=clock)

        # Act — two samples 0.2s apart
        service.process_message(MqttConfig.TOPIC_PROCESSED, _processed())
        clock.t = 0.2
        service.process_message(MqttConfig.TOPIC_PROCESSED, _processed())

        # Assert
        assert len(link.frames) == 1
        assert service.sent_count == 1

    def test_sends_again_after_interval_elapses(self):
        # Arrange
        clock = _Clock()
        bus, link = FakeBus(), FakeLink()
        service = LoraService(bus, link, fields=["soc"], min_interval=1.0, clock=clock)

        # Act — two samples 1.5s apart
        service.process_message(MqttConfig.TOPIC_PROCESSED, _processed())
        clock.t = 1.5
        service.process_message(MqttConfig.TOPIC_PROCESSED, _processed())

        # Assert
        assert len(link.frames) == 2


class TestMtuGuard:
    def test_oversized_frame_is_dropped(self):
        # Arrange — a tiny MTU forces the frame over the limit
        bus, link = FakeBus(), FakeLink()
        service = LoraService(bus, link, fields=["velocity", "soc"], max_bytes=5, clock=_Clock())

        # Act
        service.process_message(MqttConfig.TOPIC_PROCESSED, _processed())

        # Assert
        assert link.frames == []
        assert service.sent_count == 0
