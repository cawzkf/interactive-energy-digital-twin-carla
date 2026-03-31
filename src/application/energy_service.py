import queue
import threading

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.domain.dtos import UpdateResponseDto
from src.infra.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Shared state
#
# _energy_state : last UpdateResponseDto received from the queue.
#                 None until main.py sends the first tick.
#
# _state_lock   : ensures the consumer thread does not write while
#                 FastAPI is reading, preventing partial state reads.
#
# _energy_queue : queue injected by main.py via set_queue().
#                 Not initialized here — the module does not know the queue
#                 until main.py calls set_queue().
# ---------------------------------------------------------------------------

_energy_state: UpdateResponseDto | None = None
_state_lock = threading.Lock()
_energy_queue: queue.Queue | None = None

# ---------------------------------------------------------------------------
#  FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Energy Digital Twin Service",
    description=(
        "Expõe em tempo real os dados energéticos calculados pelo "
        "VehicleEnergySystem integrado ao CARLA."
    ),
    version="1.0.0",
)

