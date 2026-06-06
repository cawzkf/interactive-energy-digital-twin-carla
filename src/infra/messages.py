from src.exceptions import (
    AcquisitionSourceError,
    MarchForceError,
    MessageBusError,
    RepositoryError,
    TelemetryLinkError,
)

_FRIENDLY: dict[type, str] = {
    MessageBusError: (
        "Não foi possível falar com o broker MQTT. "
        "Verifique se ele está no ar (make up)."
    ),
    RepositoryError: (
        "Não foi possível conectar ao banco de telemetria. "
        "Verifique o TimescaleDB (make up)."
    ),
    AcquisitionSourceError: (
        "A fonte de dados não respondeu. Em CARLA, confira se o servidor está "
        "rodando (make carla); ou use ACQ_SOURCE=sim."
    ),
    TelemetryLinkError: (
        "O enlace LoRa não pôde ser aberto. Confira o módulo/porta serial "
        "ou use LORA_LINK=log."
    ),
}


def friendly(error: Exception) -> str:
    """Translate an exception into a user-facing message in pt-BR."""
    for kind, message in _FRIENDLY.items():
        if isinstance(error, kind):
            return message
    if isinstance(error, MarchForceError):
        return f"Falha no sistema de telemetria: {error}"
    return f"Erro inesperado: {error}"
