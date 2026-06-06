"""Offline end-to-end pipeline smoke test (no broker, database or CARLA)."""
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application.processing_service import ProcessingService  # noqa: E402
from src.domain.dtos import RawTelemetryDto  # noqa: E402
from src.infra.config import MqttConfig  # noqa: E402
from src.infra.sources import sim_source  # noqa: E402
from tests.fakes import FakeBus, FakeRepository  # noqa: E402


def main() -> int:
    bus, repo = FakeBus(), FakeRepository()
    processing = ProcessingService(bus, repo)

    for i, state in enumerate(itertools.islice(sim_source(real_time=False), 30)):
        raw = RawTelemetryDto(
            session_id="smoke", timestamp=1700000000.0 + i * 0.1,
            velocity=state.velocity, acceleration=state.acceleration, dt=state.dt,
        )
        processing.process_message(MqttConfig.TOPIC_RAW, raw.model_dump_json())

    assert len(bus.published) == 30
    assert len(repo.inserted) == 30

    last = json.loads(bus.published[-1][1])
    print("Processed sample delivered to the HUD:")
    print(json.dumps(last, indent=2, ensure_ascii=False))
    print(f"\nOK: {len(bus.published)} published, {len(repo.inserted)} persisted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
