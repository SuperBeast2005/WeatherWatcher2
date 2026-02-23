from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import sqlite3
import uuid
from datetime import datetime, timedelta

app = FastAPI(title="WeatherWatcher API")

DB = "weatherwatcher.db"

# -------------------
# Helpers
# -------------------
def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def now():
    return datetime.utcnow().isoformat()

# -------------------
# Models
# -------------------
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
    espId: Optional[str]
    thresholds: PlantThresholds
    recommendations: List[Recommendation] = []

class ESPCreate(BaseModel):
    name: str
    ip: str

# -------------------
# REST: Plants
# -------------------
@app.get("/api/plants")
def get_plants():
    c = db()
    plants = c.execute("SELECT * FROM plants").fetchall()
    return [dict(p) for p in plants]

@app.get("/api/plants/{plant_id}")
def get_plant(plant_id: str):
    c = db()
    plant = c.execute("SELECT * FROM plants WHERE id=?", (plant_id,)).fetchone()
    if not plant:
        raise HTTPException(404, "Plant not found")

    current = c.execute(
        "SELECT * FROM sensor_data WHERE plant_id=? ORDER BY timestamp DESC LIMIT 1",
        (plant_id,)
    ).fetchone()

    history = c.execute(
        "SELECT * FROM sensor_data WHERE plant_id=? ORDER BY timestamp DESC LIMIT 100",
        (plant_id,)
    ).fetchall()

    thresholds = c.execute(
        "SELECT * FROM plant_thresholds WHERE plant_id=?",
        (plant_id,)
    ).fetchone()

    recs = c.execute(
        "SELECT id,type,message FROM recommendations WHERE plant_id=?",
        (plant_id,)
    ).fetchall()

    return {
        **dict(plant),
        "currentData": dict(current) if current else None,
        "history": [dict(h) for h in history],
        "thresholds": dict(thresholds) if thresholds else None,
        "recommendations": [dict(r) for r in recs]
    }

@app.post("/api/plants")
def create_plant(payload: PlantCreate):
    plant_id = str(uuid.uuid4())
    c = db()

    c.execute(
        "INSERT INTO plants VALUES (?,?,?,?)",
        (plant_id, payload.espId, payload.name, payload.species)
    )

    t = payload.thresholds
    c.execute(
        """INSERT INTO plant_thresholds VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            plant_id,
            t.co2.min, t.co2.low, t.co2.high, t.co2.max,
            t.temperature.min, t.temperature.low, t.temperature.high, t.temperature.max,
            t.humidity.min, t.humidity.low, t.humidity.high, t.humidity.max,
            t.light.min, t.light.low, t.light.high, t.light.max
        )
    )

    for r in payload.recommendations:
        c.execute(
            "INSERT INTO recommendations VALUES (?,?,?,?,?)",
            (r.id, plant_id, r.type, r.message, now())
        )

    c.commit()
    return {"id": plant_id}

@app.delete("/api/plants/{plant_id}", status_code=204)
def delete_plant(plant_id: str):
    c = db()
    c.execute("DELETE FROM plants WHERE id=?", (plant_id,))
    c.commit()

@app.get("/api/plants/{plant_id}/history")
def plant_history(plant_id: str, hours: int = 24):
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    c = db()
    data = c.execute(
        "SELECT * FROM sensor_data WHERE plant_id=? AND timestamp>=?",
        (plant_id, since)
    ).fetchall()
    return [dict(d) for d in data]

# -------------------
# REST: ESPs
# -------------------
@app.get("/api/esps")
def get_esps():
    c = db()
    return [dict(e) for e in c.execute("SELECT * FROM esps").fetchall()]

@app.post("/api/esps")
def create_esp(payload: ESPCreate):
    esp_id = str(uuid.uuid4())
    c = db()
    c.execute(
        "INSERT INTO esps (id,name,ip,status) VALUES (?,?,?,?)",
        (esp_id, payload.name, payload.ip, "offline")
    )
    c.commit()
    return {"id": esp_id}

@app.delete("/api/esps/{esp_id}", status_code=204)
def delete_esp(esp_id: str):
    c = db()
    c.execute("DELETE FROM esps WHERE id=?", (esp_id,))
    c.commit()

# -------------------
# WebSocket
# -------------------
clients: List[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.append(ws)

    try:
        while True:
            msg = await ws.receive_json()
            # subscribe currently ignored (broadcast-only)
    except WebSocketDisconnect:
        clients.remove(ws)

async def broadcast(payload: dict):
    for ws in clients:
        await ws.send_json(payload)