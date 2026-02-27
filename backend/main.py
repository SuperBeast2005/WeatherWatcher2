from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import uvicorn
from fastapi import FastAPI, HTTPException

from helpers import *
from models import *

app = FastAPI(title="WeatherWatcher API")
log = logging.getLogger("uvicorn.error")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_request())
    log.info("Started periodic ESP polling task")

# -------------------
# REST: ESPs
# -------------------
@app.get("/api/plants")
def get_plants():
    c = db()
    try:
        plants = c.execute("SELECT * FROM plant").fetchall()
        return [dict(p) for p in plants]
    except sqlite3.Error:
        log.exception("Failed to fetch plants")
        raise HTTPException(status_code=500, detail="Failed to load plants")
    finally:
        c.close()


@app.get("/api/plants/{plant_id}")
def get_plant(plant_id: str):
    c = db()
    try:
        plant = c.execute("SELECT * FROM plant WHERE id=?", (plant_id,)).fetchone()
        if not plant:
            raise HTTPException(status_code=404, detail="Plant not found")

        current = c.execute(
            "SELECT * FROM sensor_data WHERE ESP_ID=? ORDER BY timestamp DESC LIMIT 1",
            (plant["ESP_ID"],)
        ).fetchone()

        thresholds = c.execute(
            "SELECT * FROM plant_thresholds WHERE plant_id=?",
            (plant_id,)
        ).fetchone()

        recommendations = {}
        if current and thresholds:
            try:
                recommendations = evaluate_sensor_data(current, thresholds)
            except (KeyError, TypeError, ValueError):
                log.exception("Failed to evaluate sensor data for plant_id=%s", plant_id)
        else:
            log.warning(
                "Missing recommendation inputs plant_id=%s current=%s thresholds=%s",
                plant_id,
                bool(current),
                bool(thresholds),
            )

        return {
            **dict(plant),
            "currentData": dict(current) if current else None,
            "thresholds": dict(thresholds) if thresholds else None,
            "recommendations": recommendations,
        }
    except HTTPException:
        raise
    except sqlite3.Error:
        log.exception("Database error while loading plant_id=%s", plant_id)
        raise HTTPException(status_code=500, detail="Failed to load plant")
    finally:
        c.close()


@app.post("/api/plants")
def create_plant(payload: PlantCreate):
    c = db()
    try:
        time_created = now()
        c.execute(
            "INSERT INTO plant (ESP_ID, name, created_at, strain) VALUES (?,?,?,?)",
            (payload.espId, payload.name, time_created, payload.species),
        )
        plant_id = c.lastrowid
        if plant_id is None:
            raise HTTPException(status_code=500, detail="Failed to create plant")

        t = payload.thresholds
        c.execute(
            """INSERT INTO plant_thresholds VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                plant_id,
                t.co2.min,
                t.co2.low,
                t.co2.high,
                t.co2.max,
                t.temperature.min,
                t.temperature.low,
                t.temperature.high,
                t.temperature.max,
                t.humidity.min,
                t.humidity.low,
                t.humidity.high,
                t.humidity.max,
                t.light.min,
                t.light.low,
                t.light.high,
                t.light.max,
            ),
        )

        c.commit()
        log.info("Created plant id=%s name=%s", plant_id, payload.name)
        return {"id": plant_id}
    except HTTPException:
        c.rollback()
        raise
    except sqlite3.Error:
        c.rollback()
        log.exception("Database error while creating plant")
        raise HTTPException(status_code=500, detail="Failed to create plant")
    finally:
        c.close()


@app.delete("/api/plants/{plant_id}", status_code=204)
def delete_plant(plant_id: str):
    c = db()
    try:
        result = c.execute("DELETE FROM plant WHERE id=?", (plant_id,))
        c.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Plant not found")
    except HTTPException:
        raise
    except sqlite3.Error:
        c.rollback()
        log.exception("Database error while deleting plant_id=%s", plant_id)
        raise HTTPException(status_code=500, detail="Failed to delete plant")
    finally:
        c.close()


@app.get("/api/plants/{plant_id}/history")
def plant_history(plant_id: str, hours: int = 24):
    if hours <= 0:
        raise HTTPException(status_code=400, detail="hours must be > 0")

    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    c = db()
    try:
        plant = c.execute("SELECT ESP_ID FROM plant WHERE id=?", (plant_id,)).fetchone()
        if not plant:
            raise HTTPException(status_code=404, detail="Plant not found")

        esp_id = plant["ESP_ID"]
        if esp_id is None:
            raise HTTPException(status_code=400, detail="Plant has no ESP assigned")

        data = c.execute(
            "SELECT * FROM sensor_data WHERE ESP_ID=? AND timestamp>=?",
            (esp_id, since),
        ).fetchall()
        return [dict(d) for d in data]
    except HTTPException:
        raise
    except sqlite3.Error:
        log.exception("Database error while loading history for plant_id=%s", plant_id)
        raise HTTPException(status_code=500, detail="Failed to load plant history")
    finally:
        c.close()


# -------------------
# REST: ESPs
# -------------------
@app.get("/api/esps")
def get_esps():
    c = db()
    try:
        response = []
        esps = c.execute("SELECT * FROM ESP").fetchall()
        for e in esps:
            esp_id = e["esp_id"]
            name = e["name"]
            url = e["esp_url"]

            status = "offline"
            frequency = None
            temperature = None
            hwid = None

            try:
                api_response = requests.get(url, timeout=3)
                api_response.raise_for_status()
                current_sensor = api_response.json()
                content = current_sensor.get("content")
                if content and content != "null":
                    status = "online"
                    frequency = content.get("ESP_FREQ")
                    temperature = content.get("ESP_TEMP")
                    hwid = content.get("ESP_HWID")
            except (requests.RequestException, ValueError, AttributeError):
                log.warning("ESP endpoint unreachable or invalid JSON esp_id=%s url=%s", esp_id, url)

            response.append(
                {
                    "id": esp_id,
                    "name": name,
                    "url": url,
                    "status": status,
                    "frequency": frequency,
                    "temperature": temperature,
                    "hwid": hwid,
                }
            )

        return response
    except sqlite3.Error:
        log.exception("Database error while loading ESPs")
        raise HTTPException(status_code=500, detail="Failed to load ESPs")
    finally:
        c.close()


@app.post("/api/esps")
def create_esp(payload: ESPCreate):
    c = db()
    try:
        c.execute(
            "INSERT INTO ESP (name, esp_url) VALUES (?, ?)",
            (payload.name, payload.url),
        )
        c.commit()
        log.info("Created ESP name=%s url=%s", payload.name, payload.url)
        return True
    except sqlite3.Error:
        c.rollback()
        log.exception("Database error while creating ESP")
        raise HTTPException(status_code=500, detail="Failed to create ESP")
    finally:
        c.close()


@app.delete("/api/esps/{esp_id}", status_code=204)
def delete_esp(esp_id: str):
    c = db()
    try:
        result = c.execute("DELETE FROM ESP WHERE esp_id=?", (esp_id,))
        c.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="ESP not found")
    except HTTPException:
        raise
    except sqlite3.Error:
        c.rollback()
        log.exception("Database error while deleting esp_id=%s", esp_id)
        raise HTTPException(status_code=500, detail="Failed to delete ESP")
    finally:
        c.close()


if __name__ == "__main__":
    uvicorn.run(app, reload=True, port=3000, log_level="trace")
