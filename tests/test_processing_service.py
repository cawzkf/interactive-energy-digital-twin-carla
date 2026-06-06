"""Unit tests for the processing service, structured as Arrange-Act-Assert."""
import json

import pytest

from src.application.processing_service import ProcessingService, derive_dc_bus
from src.domain.diagnostics import AlertCode
from src.domain.dtos import RawTelemetryDto
from src.infra.config import MqttConfig
from tests.fakes import FakeBus, FakeRepository


def _raw(session="sess-test", velocity=30.0, accel=0.0, dt=0.1, **kw):
    return RawTelemetryDto(
        session_id=session, timestamp=1700000000.0,
        velocity=velocity, acceleration=accel, dt=dt, **kw,
    ).model_dump_json()


class TestDeriveDcBus:
    def test_discharge_yields_positive_current(self):
        # Arrange / Act
        vdc, idc = derive_dc_bus(power=1000.0, electrical_step=100.0, dt=0.1, soc=1.0,
                                 nominal_voltage=48.0)
        # Assert
        assert vdc > 0
        assert idc > 0

    def test_regen_yields_negative_current(self):
        # Arrange / Act
        _, idc = derive_dc_bus(power=-1000.0, electrical_step=100.0, dt=0.1, soc=1.0,
                               nominal_voltage=48.0)
        # Assert
        assert idc < 0

    def test_zero_dt_is_safe(self):
        # Arrange / Act
        _, idc = derive_dc_bus(power=1000.0, electrical_step=100.0, dt=0.0, soc=1.0,
                               nominal_voltage=48.0)
        # Assert
        assert idc == 0.0


class TestProcessMessage:
    @pytest.fixture
    def service_with_fakes(self):
        bus, repo = FakeBus(), FakeRepository()
        return ProcessingService(bus, repo), bus, repo

    def test_publishes_processed_sample_on_processed_topic(self, service_with_fakes):
        # Arrange
        service, bus, _ = service_with_fakes

        # Act
        service.process_message(MqttConfig.TOPIC_RAW, _raw())

        # Assert
        assert len(bus.published) == 1
        topic, payload = bus.published[0]
        assert topic == MqttConfig.TOPIC_PROCESSED
        processed = json.loads(payload)
        assert processed["session_id"] == "sess-test"
        assert processed["vdc"] > 0
        assert processed["power"] > 0
        assert 0.0 <= processed["soc"] <= 1.0

    def test_persists_sample_and_registers_session(self, service_with_fakes):
        # Arrange
        service, _, repo = service_with_fakes

        # Act
        service.process_message(MqttConfig.TOPIC_RAW, _raw())

        # Assert
        assert len(repo.inserted) == 1
        assert "sess-test" in repo.sessions

    def test_uses_measured_bus_values_when_provided(self, service_with_fakes):
        # Arrange
        service, bus, _ = service_with_fakes

        # Act
        service.process_message(MqttConfig.TOPIC_RAW, _raw(vdc=60.0, idc=3.0))

        # Assert
        processed = json.loads(bus.published[0][1])
        assert processed["vdc"] == 60.0
        assert processed["idc"] == 3.0

    def test_persist_failure_is_reported_as_alert_without_dropping_sample(self):
        # Arrange
        bus, repo = FakeBus(), FakeRepository(fail_on_insert=True)
        service = ProcessingService(bus, repo)

        # Act
        service.process_message(MqttConfig.TOPIC_RAW, _raw())

        # Assert
        assert len(bus.published) == 1  # stream not interrupted
        processed = json.loads(bus.published[0][1])
        codes = [a["code"] for a in processed["alerts"]]
        assert AlertCode.PERSIST.value in codes

    def test_forwards_position_to_processed(self, service_with_fakes):
        # Arrange
        service, bus, _ = service_with_fakes

        # Act
        service.process_message(MqttConfig.TOPIC_RAW, _raw(x=10.0, y=20.0))

        # Assert
        processed = json.loads(bus.published[0][1])
        assert processed["x"] == 10.0
        assert processed["y"] == 20.0

    def test_keeps_independent_state_per_session(self, service_with_fakes):
        # Arrange
        service, _, repo = service_with_fakes

        # Act
        service.process_message(MqttConfig.TOPIC_RAW, _raw(session="A"))
        service.process_message(MqttConfig.TOPIC_RAW, _raw(session="B"))

        # Assert
        assert set(repo.sessions) == {"A", "B"}
