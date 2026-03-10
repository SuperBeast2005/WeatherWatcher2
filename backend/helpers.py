import asyncio
import logging
import httpx
import sqlite3
from datetime import datetime, timedelta
from fastapi import WebSocket
log = logging.getLogger("uvicorn.error")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                log.error("Failed to send WS message: %s", e)

manager = ConnectionManager()


DB = "db.db"
esp_request_cycle_time = 30 #in seconds


def db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = lambda cursor, row: {
    col[0]: row[i] for i, col in enumerate(cursor.description)
    }
    return conn

def now():
    return datetime.utcnow().isoformat()

def safe_float(val):
    if val is None or val == "None" or val == "":
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def check_threshold(value, min_v, max_v, low_v, high_v):
    print(value, min_v, max_v, low_v, high_v)
    if value == "None":
        return None
    if value < min_v:
        return "too_low"
    if value > max_v:
        return "too_high"
    if value < low_v:
        return "warning_low"
    if value > high_v:
        return "warning_high"
    return None


def evaluate_sensor_data(sensor: dict, thresholds: dict) -> dict:
    results = {}

    checks = {
        "temperature": (
            sensor["env_temp"],
            thresholds["temperature_min"],
            thresholds["temperature_max"],
            thresholds["temperature_low"],
            thresholds["temperature_high"],
        ),
        "humidity": (
            sensor["env_humi"],
            thresholds["humidity_min"],
            thresholds["humidity_max"],
            thresholds["humidity_low"],
            thresholds["humidity_high"],
        ),
        "co2": (
            sensor["env_co2p"],
            thresholds["co2_min"],
            thresholds["co2_max"],
            thresholds["co2_low"],
            thresholds["co2_high"],
        ),
        "light": (
            sensor["env_brig"],
            thresholds["light_min"],
            thresholds["light_max"],
            thresholds["light_low"],
            thresholds["light_high"],
        ),
    }

    for name, (value, min_v, max_v, low_v, high_v) in checks.items():
        status = check_threshold(value, min_v, max_v, low_v, high_v)
        if status:
            results[name] = {
                "value": value,
                "status": status,
                "expected_range": [min_v, max_v],
            }

    return results

async def periodic_request():
    async with httpx.AsyncClient() as client:
        while True:
            c = db()
            try:
                list_of_esps = c.execute("SELECT * FROM ESP").fetchall()
                for esp in list_of_esps:
                    try:
                        resp = await client.get(esp["esp_url"], timeout=5)
                        resp.raise_for_status()
                        r = resp.json()
                        
                        content = r.get("content")
                        if content is None or content == "null":
                            log.debug("ESP is offline or no data: %s", esp["esp_id"])
                            continue
                        
                        # Use HWID from JSON if available, otherwise fallback
                        json_hwid = content.get("ESP_HWID") or ""
                        timestamp = content.get("TIMESTAMP") or now()

                        c.execute("""
                                  INSERT INTO sensor_data (ESP_ID,timestamp,esp_freq,esp_temp,env_temp,
                                                           env_humi,env_co2p,env_brig,ESP_HWID)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                  """,
                                  (
                                      esp["esp_id"],
                                      timestamp,
                                      safe_float(content.get("ESP_FREQ")),
                                      safe_float(content.get("ESP_TEMP")),
                                      safe_float(content.get("ENV_TEMP")),
                                      safe_float(content.get("ENV_HUMI")),
                                      safe_float(content.get("ENV_CO2P")),
                                      safe_float(content.get("ENV_BRIG")),
                                      json_hwid
                                  ))
                        c.commit()
                        
                        # Find which plant(s) belong to this ESP to notify frontend 
                        plants = c.execute("SELECT id FROM plant WHERE ESP_ID=?", (esp["esp_id"],)).fetchall()
                        for p in plants:
                            await manager.broadcast({
                                "type": "sensor_update",
                                "plantId": str(p["id"]),
                                "data": {
                                    "co2": safe_float(content.get("ENV_CO2P")),
                                    "temperature": safe_float(content.get("ENV_TEMP")),
                                    "humidity": safe_float(content.get("ENV_HUMI")),
                                    "light": safe_float(content.get("ENV_BRIG")),
                                    "timestamp": str(timestamp)
                                }
                            })
                    except (httpx.HTTPError, ValueError, KeyError) as e:
                        log.warning("Polling error for ESP name=%s id=%s: %s", esp["name"], esp["esp_id"], e)
            except Exception as e:
                log.exception("Fatal error in periodic_request loop")
            finally:
                c.close()

            await asyncio.sleep(esp_request_cycle_time)
