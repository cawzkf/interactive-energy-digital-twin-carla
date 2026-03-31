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


@app.get("/energy/state")
def get_energy_state() -> JSONResponse:
    """
    Retorna o último estado energético calculado pelo VehicleEnergySystem.

    Campos retornados:
    - power               : Potência mecânica instantânea (W)
    - mech_energy_total   : Energia mecânica acumulada (J)
    - soc                 : State of Charge da bateria (0.0 a 1.0)
    - distance_total      : Distância percorrida acumulada (m)
    - avg_power           : Média de potência das últimas N amostras (W)
    - specific_consumption: Consumo específico (Wh/m)
    - estimated_autonomy  : Autonomia estimada com base no SoC e avg_power (s)

    Retorna 503 enquanto o main.py ainda não enviou o primeiro tick.
    """
    with _state_lock:
        current = _energy_state

    if current is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Aguardando primeiro tick do CARLA..."},
        )

    return JSONResponse(
        status_code=200,
        content={
            "power": current.power,
            "mech_energy_total": current.mech_energy_total,
            "soc": current.soc,
            "distance_total": current.distance_total,
            "avg_power": current.avg_power,
            "specific_consumption": current.specific_consumption,
            "estimated_autonomy": current.estimated_autonomy,
        },
    )


@app.get("/health")
def health() -> JSONResponse:
    """
    Health check — o manual_control_energy.py pode usar esta rota para
    aguardar o serviço estar disponível antes de iniciar o HUD.
    """
    return JSONResponse(status_code=200, content={"status": "ok"})




def set_queue(q: queue.Queue) -> None:
    """
    Injects the shared queue produced by main.py.

    Must be called once before uvicorn.run(), so that the consumer thread
    is already running when the first ticks arrive.

    :param q: queue.Queue(maxsize=1) instance created in main.py
    """
    global _energy_queue
    _energy_queue = q
    _start_consumer_thread()
    logger.info("energy_queue_injected")


