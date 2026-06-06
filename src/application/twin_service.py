import base64
import json

import requests

from src.domain.aas_model import TELEMETRY_MODEL
from src.domain.dtos import (
    ProcessedTelemetryDto,
    UpdateRequestDto,
    UpdateResponseDto,
)
from src.infra.logger import get_logger

logger = get_logger(__name__)

SUBMODEL_IDS = {
    "OperationalState": "https://example.com/ids/sm/2064_2231_2062_1810",
    "Battery": "https://example.com/ids/sm/8164_2231_2062_3248",
    "EnergyEfficiency": "https://marchforce.org/sm/energyefficiency",
}


def _encode_id(raw_id: str) -> str:
    return base64.urlsafe_b64encode(raw_id.encode()).decode().rstrip("=")


class TwinService:
    def __init__(self, basyx_url: str = "http://localhost:8081") -> None:
        self.basyx_url = basyx_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        self._op_state_base = (
            f"{self.basyx_url}/submodels/"
            f"{_encode_id(SUBMODEL_IDS['OperationalState'])}"
            f"/submodel-elements"
        )
        self._battery_base = (
            f"{self.basyx_url}/submodels/"
            f"{_encode_id(SUBMODEL_IDS['Battery'])}"
            f"/submodel-elements"
        )
        self._efficiency_base = (
            f"{self.basyx_url}/submodels/"
            f"{_encode_id(SUBMODEL_IDS['EnergyEfficiency'])}"
            f"/submodel-elements"
        )

    def check_connection(self) -> bool:
        try:
            resp = self._session.get(
                f"{self.basyx_url}/submodels/"
                f"{_encode_id(SUBMODEL_IDS['EnergyEfficiency'])}"
            )
            resp.raise_for_status()
            logger.info("basyx_connection_ok", url=self.basyx_url)
            return True
        except requests.RequestException as e:
            logger.error("basyx_connection_failed", url=self.basyx_url, error=str(e))
            return False

    def _patch_value(self, base_url: str, id_short: str, value: str) -> None:
        url = f"{base_url}/{id_short}/$value"
        self._session.patch(url, data=json.dumps(value))

    def sync(
        self,
        request: UpdateRequestDto,
        response: UpdateResponseDto,
    ) -> None:
        try:
            self._patch_value(
                self._op_state_base, "Velocity", str(round(request.velocity, 4))
            )
            self._patch_value(
                self._op_state_base,
                "Acceleration",
                str(round(request.acceleration, 4)),
            )
            self._patch_value(
                self._op_state_base,
                "InstantaneousPower",
                str(round(response.power, 2)),
            )
            self._patch_value(
                self._op_state_base,
                "AccumulatedEnergy",
                str(round(response.mech_energy_total, 2)),
            )
            self._patch_value(
                self._battery_base,
                "StateOfCharge",
                str(round(response.soc * 100)),
            )
            self._patch_value(
                self._battery_base,
                "ElectricalEnergyFlow",
                str(round(response.electrical_used_or_recovered, 2)),
            )
            logger.debug(
                "basyx_sync_ok",
                power=response.power,
                soc=response.soc,
            )
        except requests.RequestException as e:
            logger.warning("basyx_sync_failed", error=str(e))

    def sync_processed(self, p: ProcessedTelemetryDto) -> None:
        """Update the EnergyEfficiency submodel KPIs from a processed sample.

        Model-driven from the canonical telemetry model. The raw time series is
        exposed via the IDTA TimeSeries LinkedSegment (TimescaleDB), not PATCHed
        per sample.
        """
        try:
            for id_short, field, scale in TELEMETRY_MODEL["EnergyEfficiency"]:
                value = getattr(p, field) * scale
                self._patch_value(self._efficiency_base, id_short, str(round(value, 4)))
            logger.debug("aas_sync_ok", distance=p.distance, autonomy=p.autonomy)
        except requests.RequestException as e:
            logger.warning("aas_sync_failed", error=str(e))
