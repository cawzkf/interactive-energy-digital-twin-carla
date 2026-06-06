import math
import time

from src.application.ports import TelemetrySource
from src.domain.dtos import UpdateRequestDto
from src.exceptions import AcquisitionSourceError
from src.infra.logger import get_logger

logger = get_logger(__name__)


def carla_source() -> TelemetrySource:
    try:
        from src.infra.carla_client import CarlaClient

        client = CarlaClient()
        client.connect()
        client.spawn_vehicle()
    except Exception as e:
        raise AcquisitionSourceError(f"CARLA source unavailable: {e}") from e

    try:
        from src.infra.keyboard_control import read_control

        has_keyboard = True
    except Exception:
        has_keyboard = False

    manual = False
    prev_toggle = False
    logger.info("carla_source_ready", keyboard=has_keyboard)
    try:
        while True:
            if has_keyboard:
                ctrl = read_control()
                if ctrl["throttle"] or ctrl["brake"] or ctrl["steer"]:
                    manual = True
                if ctrl["toggle"] and not prev_toggle:
                    manual = not manual
                    logger.info("control_mode", manual=manual)
                prev_toggle = ctrl["toggle"]
                if manual:
                    client.apply_manual(
                        ctrl["throttle"], ctrl["steer"], ctrl["brake"], ctrl["reverse"]
                    )
                else:
                    client.set_autopilot(True)
            state = client.tick()
            if state is not None:
                yield state
            time.sleep(0.08)
    finally:
        client.destroy()


def _velocity_profile(t: float) -> tuple[float, float]:
    if t < 15:
        acc = 2.0
        vel = acc * t
    elif t < 40:
        acc = 0.0
        vel = 30.0
    else:
        acc = -1.5
        vel = max(0.0, 30.0 + acc * (t - 40))
        if vel == 0.0:
            acc = 0.0
    return vel, acc


_TRACK_A = 120.0
_TRACK_B = 70.0
_TRACK_PERIMETER = math.pi * (
    3 * (_TRACK_A + _TRACK_B)
    - math.sqrt((3 * _TRACK_A + _TRACK_B) * (_TRACK_A + 3 * _TRACK_B))
)


def sim_source(dt: float = 0.1, real_time: bool = True) -> TelemetrySource:
    t = 0.0
    distance = 0.0
    while True:
        vel, acc = _velocity_profile(t % 60.0)
        theta = (distance / _TRACK_PERIMETER) * 2 * math.pi
        x = _TRACK_A * math.cos(theta)
        y = _TRACK_B * math.sin(theta)
        yield UpdateRequestDto(velocity=vel, acceleration=acc, dt=dt, x=x, y=y)
        distance += vel * dt
        t += dt
        if real_time:
            time.sleep(dt)
