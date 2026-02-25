from typing import Optional, List

from pydantic import BaseModel


class SensorData(BaseModel):
    co2: int
    temperature: float
    humidity: float
    light: int
    timestamp: str

class ThresholdRange(BaseModel):
    min: float
    low: float
    high: float
    max: float

class PlantThresholds(BaseModel):
    co2: ThresholdRange
    temperature: ThresholdRange
    humidity: ThresholdRange
    light: ThresholdRange

class Recommendation(BaseModel):
    id: str
    type: str
    message: str

class PlantCreate(BaseModel):
    name: str
    species: str
    espId: Optional[int]
    thresholds: PlantThresholds

class ESPCreate(BaseModel):
    name: str
    url: str