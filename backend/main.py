from datetime import datetime

from fastapi import FastAPI
from typing import Union
from pydantic import BaseModel

class Measurement(BaseModel):
    user_id: int
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

@app.post("/measurement")
def create_measurement(measurement: Measurement):
    print(measurement)
    return measurement