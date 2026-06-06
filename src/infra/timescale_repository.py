from datetime import UTC, datetime

import psycopg
from psycopg.types.json import Jsonb

from src.application.ports import TelemetryRepository
from src.domain.dtos import ProcessedTelemetryDto
from src.exceptions import RepositoryError
from src.infra.config import DbConfig
from src.infra.logger import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    source      TEXT NOT NULL DEFAULT 'carla',
    note        TEXT
);

CREATE TABLE IF NOT EXISTS telemetry (
    time                 TIMESTAMPTZ      NOT NULL,
    session_id           TEXT             NOT NULL REFERENCES sessions(id),
    velocity             DOUBLE PRECISION,
    acceleration         DOUBLE PRECISION,
    vdc                  DOUBLE PRECISION,
    idc                  DOUBLE PRECISION,
    power                DOUBLE PRECISION,
    energy               DOUBLE PRECISION,
    soc                  DOUBLE PRECISION,
    distance             DOUBLE PRECISION,
    avg_power            DOUBLE PRECISION,
    specific_consumption DOUBLE PRECISION,
    autonomy             DOUBLE PRECISION,
    x                    DOUBLE PRECISION,
    y                    DOUBLE PRECISION,
    alerts               JSONB
);

SELECT create_hypertable('telemetry', 'time', if_not_exists => TRUE);
"""


class TimescaleRepository(TelemetryRepository):
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or DbConfig.dsn()
        try:
            self._conn = psycopg.connect(self.dsn, autocommit=True)
        except psycopg.Error as e:
            raise RepositoryError(f"Could not connect to TimescaleDB: {e}") from e

    def init_schema(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(_SCHEMA)
        logger.info("timescale_schema_ready")

    def ensure_session(self, session_id: str, source: str = "carla") -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (id, source) VALUES (%s, %s) "
                "ON CONFLICT (id) DO NOTHING",
                (session_id, source),
            )

    def insert(self, sample: ProcessedTelemetryDto) -> None:
        ts = datetime.fromtimestamp(sample.timestamp, tz=UTC)
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO telemetry (
                    time, session_id, velocity, acceleration, vdc, idc,
                    power, energy, soc, distance, avg_power,
                    specific_consumption, autonomy, x, y, alerts
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ts, sample.session_id, sample.velocity, sample.acceleration,
                    sample.vdc, sample.idc, sample.power, sample.energy, sample.soc,
                    sample.distance, sample.avg_power, sample.specific_consumption,
                    sample.autonomy, sample.x, sample.y,
                    Jsonb([a.model_dump(mode="json") for a in sample.alerts]),
                ),
            )

    def list_sessions(self) -> list[dict]:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id, s.started_at, s.source, count(t.*) AS samples,
                       max(t.distance) AS distance, min(t.soc) AS final_soc
                FROM sessions s
                LEFT JOIN telemetry t ON t.session_id = s.id
                GROUP BY s.id, s.started_at, s.source
                ORDER BY s.started_at DESC
                """
            )
            cols = [c.name for c in cur.description]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    def get_history(self, session_id: str, limit: int = 5000) -> list[dict]:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT time, velocity, acceleration, vdc, idc, power, energy,
                       soc, distance, avg_power, specific_consumption, autonomy,
                       x, y, alerts
                FROM telemetry
                WHERE session_id = %s
                ORDER BY time ASC
                LIMIT %s
                """,
                (session_id, limit),
            )
            cols = [c.name for c in cur.description]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()
