from fastapi import APIRouter
from logging import getLogger
from ..db import cursor, conn
from ..model.models import *

log = getLogger(__name__)

router = APIRouter(
    prefix="/ideal_value",
    tags=["ideal_value"]
)

@router.post("")
def create_ideal_value(ideal_value: Ideal_Value):
    log.info("Adding ideal value: %s", ideal_value)

    cursor.execute("""
        INSERT INTO ideal_values
        (unit, low, very_low, high, very_high)
        VALUES (?, ?, ?, ?, ?)
    """, (ideal_value.unit, ideal_value.low, ideal_value.very_low, ideal_value.high, ideal_value.very_high))

    conn.commit()

@router.get("/{id}")
def get_ideal_value_by_id(id: int):
    cursor.execute("SELECT * FROM ideal_values WHERE id = ?", (id,))
    return cursor.fetchone()
