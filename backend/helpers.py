import asyncio
import sqlite3
import httpx
import sqlite3
from datetime import datetime, timedelta


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
        c = db()
        list_of_esps = c.execute("SELECT * FROM ESP").fetchall()
        for esp in list_of_esps:
            print("ESP found in db: " + esp["name"])
        while True:
            try:
                for esp in list_of_esps:
                    r = (await client.get(esp["esp_url"])).json()
                    if r["content"] is None or r["content"] == "null":
                        print("ESP is offline: " + esp["espid"])
                        continue
                    else:
                        #print("Sucefully fetched information from ESP: " + str(r["id"]))
                        #print(r["content"])
                        c.execute("""
                                  INSERT INTO sensor_data (ESP_ID,timestamp,esp_freq,esp_temp,env_temp,
                                                           env_humi,env_co2p,env_brig,ESP_HWID)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                  """,
                                  (
                                      r["id"],r["content"]["TIMESTAMP"],r["content"]["ESP_FREQ"],r["content"]["ESP_TEMP"],
                                      r["content"]["ENV_TEMP"],r["content"]["ENV_HUMI"],r["content"]["ENV_CO2P"],r["content"]["ENV_BRIG"],r["content"]["ESP_HWID"]
                                  ))
                        c.commit()
            except Exception as e:
                print("Error:", e)

            await asyncio.sleep(esp_request_cycle_time)
