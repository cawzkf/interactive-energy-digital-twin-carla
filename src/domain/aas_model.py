"""Canonical telemetry model — single source for the AAS submodels and OPC UA.

Built so the communication layer (OPC UA) is derived FROM the model structure,
not from an arbitrary list. Grouped by AAS submodel:

- TimeSeries (IDTA 02008): raw dynamic telemetry (the longitudinal-dynamics state).
- EnergyEfficiency (energy management / ISO 50001 derived KPIs).
- TechnicalData (IDTA 02003): static vehicle parameters (handled separately).

Each variable: (idShort, processed-telemetry field, scale).
"""

TELEMETRY_MODEL: dict[str, list[tuple[str, str, float]]] = {
    "TimeSeries": [
        ("Velocity", "velocity", 1.0),
        ("Acceleration", "acceleration", 1.0),
        ("InstantaneousPower", "power", 1.0),
        ("AccumulatedEnergy", "energy", 1.0),
        ("DcVoltage", "vdc", 1.0),
        ("DcCurrent", "idc", 1.0),
        ("StateOfCharge", "soc", 100.0),
    ],
    "EnergyEfficiency": [
        ("Distance", "distance", 1.0),
        ("AveragePower", "avg_power", 1.0),
        ("SpecificConsumption", "specific_consumption", 1.0),
        ("Autonomy", "autonomy", 1.0),
    ],
}

TELEMETRY_VARIABLES: list[tuple[str, str, float]] = [
    var for variables in TELEMETRY_MODEL.values() for var in variables
]
