from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from models import *
from helpers import *

app = FastAPI()

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



# -------------------
# REST: Plants
# -------------------
@app.get("/api/plants")
def get_plants():
    c = db()
    plants = c.execute("SELECT * FROM plant").fetchall()
    return [dict(p) for p in plants]

@app.get("/api/plants/{plant_id}")
def get_plant(plant_id: str):
    c = db()
    plant = c.execute("SELECT * FROM plant WHERE id=?", (plant_id,)).fetchone()
    if not plant:
        raise HTTPException(404, "Plant not found")

    print(plant)

    current = c.execute(
        "SELECT * FROM sensor_data WHERE ESP_ID=? ORDER BY timestamp DESC LIMIT 1",
        (plant["ESP_ID"],)
    ).fetchone()

    thresholds = c.execute(
        "SELECT * FROM plant_thresholds WHERE plant_id=?",
        (plant_id,)
    ).fetchone()

    recs = evaluate_sensor_data(current, thresholds)
    print(recs)

    return {
        **dict(plant),
        "currentData": dict(current) if current else None,
        "thresholds": dict(thresholds) if thresholds else None,
        "recommendations": recs
    }

@app.post("/api/plants")
def create_plant(payload: PlantCreate):
    c = db()

    time_created = now()

    c.execute(
        "INSERT INTO plant VALUES (null,?,?,?,?)",
        (payload.espId, payload.name, time_created , payload.species)
    )

    plant_id = c.execute("SELECT id FROM plant WHERE created_at=?",
                         (time_created,)).fetchone()["id"]
    print(plant_id)


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

    c.commit()
    return {"id": plant_id}

@app.delete("/api/plants/{plant_id}", status_code=204)
def delete_plant(plant_id: str):
    c = db()
    c.execute("DELETE FROM plant WHERE id=?", (plant_id,))
    c.commit()

@app.get("/api/plants/{plant_id}/history")
def plant_history(plant_id: str, hours: int = 24):
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    c = db()
    esp_id = c.execute("SELECT ESP_ID FROM plant WHERE id=?", (plant_id,)).fetchone()["ESP_ID"]
    print(esp_id)
    data = c.execute(
        "SELECT * FROM sensor_data WHERE ESP_ID=? AND timestamp>=?",
        (esp_id, since)
    ).fetchall()
    return data

# -------------------
# REST: ESPs
# -------------------
@app.get("/api/esps")
def get_esps():
    c = db()
    response = []
    for e in c.execute("SELECT * FROM ESP").fetchall():
        esp_id = e["esp_id"]
        name = e["name"]
        url = e["esp_url"]

        status = "offline"
        frequency = None
        temperature = None
        hwid = None

        current_sensor = requests.get(url).json()

        if current_sensor["content"] and current_sensor["content"] != "null":
            status = "online"
            frequency = current_sensor["content"]["ESP_FREQ"]
            temperature = current_sensor["content"]["ESP_TEMP"]
            hwid = current_sensor["content"]["ESP_HWID"]

        r = {
            "id" : esp_id,
            "name" : name,
            "url" : url,
            "status" : status,
            "frequency" : frequency,
            "temperature" : temperature,
            "hwid" : hwid,
        }

        response.append(r)

    return [dict(e) for e in c.execute("SELECT * FROM ESP").fetchall()]

@app.post("/api/esps")
def create_esp(payload: ESPCreate):
    c = db()
    c.execute(
        "INSERT INTO ESP (esp_id,name,esp_url) VALUES (null,?,?)",
        (payload.name, payload.url)
    )
    c.commit()
    return True

@app.delete("/api/esps/{esp_id}", status_code=204)
def delete_esp(esp_id: str):
    c = db()
    c.execute("DELETE FROM ESP WHERE esp_id=?", (esp_id,))
    c.commit()
