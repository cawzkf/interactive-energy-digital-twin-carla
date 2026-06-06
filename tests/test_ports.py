"""Unit tests for the application ports, structured as Arrange-Act-Assert."""
import pytest

from src.application.ports import MessageBus, TelemetryRepository
from tests.fakes import FakeBus, FakeRepository


class TestPortsAreAbstract:
    def test_message_bus_cannot_be_instantiated(self):
        # Act / Assert
        with pytest.raises(TypeError):
            MessageBus()

    def test_repository_cannot_be_instantiated(self):
        # Act / Assert
        with pytest.raises(TypeError):
            TelemetryRepository()


class TestFakesHonorContracts:
    def test_fake_bus_is_a_message_bus(self):
        # Arrange / Act / Assert
        assert isinstance(FakeBus(), MessageBus)

    def test_fake_repository_is_a_repository(self):
        # Arrange / Act / Assert
        assert isinstance(FakeRepository(), TelemetryRepository)


class TestIncompleteImplementationRejected:
    def test_missing_method_blocks_instantiation(self):
        # Arrange — only one of the required methods is implemented
        class Incomplete(MessageBus):
            def connect(self):
                pass

        # Act / Assert
        with pytest.raises(TypeError):
            Incomplete()
