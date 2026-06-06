"""Unit tests for the telemetry sources, structured as Arrange-Act-Assert."""
import itertools

import pytest

from src.domain.dtos import UpdateRequestDto
from src.exceptions import AcquisitionSourceError
from src.infra.sources import carla_source, sim_source


class TestSimSource:
    def test_yields_update_requests(self):
        # Arrange
        generator = sim_source(dt=0.1, real_time=False)
        # Act
        samples = list(itertools.islice(generator, 5))
        # Assert
        assert len(samples) == 5
        assert all(isinstance(s, UpdateRequestDto) for s in samples)

    def test_profile_starts_from_rest_and_accelerates(self):
        # Arrange
        generator = sim_source(dt=0.1, real_time=False)
        # Act
        first = next(generator)
        # Assert
        assert first.velocity == 0.0
        assert first.acceleration > 0.0

    def test_generates_track_positions(self):
        # Arrange
        generator = sim_source(dt=0.1, real_time=False)
        # Act
        points = list(itertools.islice(generator, 60))
        # Assert — every sample has a position and the car moves along the track
        assert all(p.x is not None and p.y is not None for p in points)
        assert len({round(p.x, 2) for p in points}) > 1


class TestCarlaSource:
    def test_wraps_unavailable_carla_in_layer_exception(self):
        # Arrange — carla is not installed in the test environment
        generator = carla_source()
        # Act / Assert — must surface the layer exception, not a raw ImportError
        with pytest.raises(AcquisitionSourceError):
            next(generator)
