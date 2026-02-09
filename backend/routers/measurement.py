from fastapi import APIRouter
from logging import getLogger
from ..db import cursor, conn
from ..model.models import Measurement

log = getLogger(__name__)

router = APIRouter(
    prefix="/measurement",
    tags=["measurement"]
)

@router.get("/{id}")
def get_measurement(id: int):
    cursor.execute("SELECT * FROM measurement WHERE id = ?", (id,))
    return cursor.fetchone()

@router.post("")
def create_measurement(measurement: Measurement):
    log.info("Adding measurement: %s", measurement)

    param = """
        INSERT INTO measurement
        (timestamp, esp_freq, esp_temp, env_temp, env_humi, env_co2p, env_brig)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    cursor.execute(param, (
        measurement.timestamp,
        measurement.esp_freq,
        measurement.esp_temp,
        measurement.env_temp,
        measurement.env_humi,
        measurement.env_co2p,
        measurement.env_brig
    ))

    conn.commit()
    return measurement
