import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx
import sqlite3
from datetime import datetime, timedelta
log = logging.getLogger("uvicorn.error")


DB = "db.db"
esp_request_cycle_time = 30 #in seconds

gmail_user = "weatherwatcher.provadis@gmail.com"
gmail_pwd = "Provadis123"
alert_recipients = [gmail_user]


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
    previous_status_by_esp_id = {}
    async with httpx.AsyncClient() as client:
        c = db()
        while True:
            list_of_esps = c.execute("SELECT * FROM ESP").fetchall()
            for esp in list_of_esps:
                esp_id = esp["esp_id"]
                esp_name = esp["name"]
                esp_url = esp["esp_url"]
                current_status = "offline"

                try:
                    response = await client.get(esp_url, timeout=5.0)
                    response.raise_for_status()
                    r = response.json()
                    content = r.get("content")

                    if content is not None and content != "null":
                        current_status = "online"
                        c.execute(
                            """
                            INSERT INTO sensor_data (ESP_ID,timestamp,esp_freq,esp_temp,env_temp,
                                                     env_humi,env_co2p,env_brig,ESP_HWID)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                r["id"], content["TIMESTAMP"], content["ESP_FREQ"], content["ESP_TEMP"],
                                content["ENV_TEMP"], content["ENV_HUMI"], content["ENV_CO2P"], content["ENV_BRIG"], content["ESP_HWID"]
                            ),
                        )
                        c.commit()
                except Exception as e:
                    log.error("Polling failed for esp_id=%s url=%s: %s", esp_id, esp_url, e)

                previous_status = previous_status_by_esp_id.get(esp_id)
                if previous_status == "online" and current_status == "offline":
                    log.error("ESP is offline: %s (%s)", esp_name, esp_id)
                    send_email(
                        subject=f"ESP offline: {esp_name}",
                        body=f"ESP mit ID {esp_id} ({esp_name}) ist offline.",
                        recipients=alert_recipients,
                    )
                elif previous_status == "offline" and current_status == "online":
                    log.info("ESP back online: %s (%s)", esp_name, esp_id)

                previous_status_by_esp_id[esp_id] = current_status

            await asyncio.sleep(esp_request_cycle_time)

def send_email(subject, body, recipients=None):
    if recipients is None:
        recipients = alert_recipients
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = ', '.join(recipients)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
        smtp_server.login(gmail_user, gmail_pwd)
        smtp_server.sendmail(gmail_user, recipients, msg.as_string())
    log.info("Alert email sent to %s", ", ".join(recipients))
