class MarchForceError(Exception):
    """Root of every error raised by the project."""


class DomainError(MarchForceError):
    """Invalid state or rule violation in the energy/diagnostics domain."""


class InvalidParameterError(DomainError):
    """A domain object received an out-of-range/invalid parameter."""


class InfraError(MarchForceError):
    """Failure in an external adapter (broker, database, source...)."""


class MessageBusError(InfraError):
    """The MQTT logical bus could not connect/publish/subscribe."""


class RepositoryError(InfraError):
    """The persistence backend (TimescaleDB) failed."""


class AcquisitionSourceError(InfraError):
    """A telemetry source (CARLA, RS485 bridge, simulator) failed."""


class TelemetryLinkError(InfraError):
    """An external telemetry link (e.g. the LoRa link to the box) failed."""


class ApplicationError(MarchForceError):
    """Failure orchestrating the use cases (acquisition/processing/exposure)."""


class ProcessingError(ApplicationError):
    """The processing service could not handle an incoming sample."""
