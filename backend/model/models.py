from datetime import datetime
from pydantic import BaseModel

class ESP(BaseModel):
    hardware_id: str
    name: str

class Plant(BaseModel):
    ESP_ID: int
    name: str
    created_at: datetime
    strain: str
    ideal_value_id: int

class Ideal_Value(BaseModel):
    unit: str
    very_high: float
    high: float
    low: float
    very_low: float


class Measurement(BaseModel):
    timestamp: datetime
    esp_freq: float
    esp_temp: float
    env_temp: float
    env_humi: float
    env_co2p: float
    env_brig: float