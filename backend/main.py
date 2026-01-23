from datetime import datetime
from logging import getLogger
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import os.path
import sqlite3

log = getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "db.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.row_factory = lambda cursor, row: {col[0] : row[i] for i,col in enumerate(cursor.description)}
cursor = conn.cursor()

class Measurement(BaseModel):

    timestamp: datetime
    esp_freq: float
    esp_temp: float
    env_temp: float
    env_humi: float
    env_co2p: float
    env_brig: float



app = FastAPI()
@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/measurement/{id}")
def get_measurement(id: int):
    cursor.execute("SELECT * FROM measurement WHERE id = ?", (id,))
    return cursor.fetchone()


@app.post("/measurement")
def create_measurement(measurement: Measurement) -> Measurement:
    log.info("Adding measurement to database: %s", measurement)

    data = (measurement.timestamp, measurement.esp_freq, measurement.esp_temp, measurement.env_temp,measurement.env_humi,measurement.env_co2p,measurement.env_brig)
    param = """INSERT INTO measurement
               (timestamp, esp_freq, esp_temp, env_temp, env_humi, env_co2p, env_brig)
            VALUES (?, ?, ?, ?, ?, ?, ?)"""
    cursor.execute(param, data)
    conn.commit()
    return measurement

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)