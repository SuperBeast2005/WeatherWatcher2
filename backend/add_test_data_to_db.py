import os
import random
import sqlite3
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "db.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.row_factory = lambda cursor, row: {col[0] : row[i] for i,col in enumerate(cursor.description)}
cur = conn.cursor()

base_time = datetime.now()

for i in range(20):
    timestamp = base_time - timedelta(minutes=i * 5)

    esp_freq = round(random.uniform(160.0, 240.0), 2)   # MHz
    esp_temp = round(random.uniform(30.0, 70.0), 2)     # °C
    env_temp = round(random.uniform(18.0, 30.0), 2)     # °C
    env_humi = round(random.uniform(30.0, 70.0), 2)     # %
    env_co2p = round(random.uniform(400.0, 2000.0), 2)  # ppm
    env_brig = round(random.uniform(0.0, 1000.0), 2)    # Lux

    cur.execute("""
        INSERT INTO measurement (
            timestamp,
            esp_freq,
            esp_temp,
            env_temp,
            env_humi,
            env_co2p,
            env_brig
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp.isoformat(sep=" "),
        esp_freq,
        esp_temp,
        env_temp,
        env_humi,
        env_co2p,
        env_brig
    ))

conn.commit()
conn.close()

print("20 Testdatensätze erfolgreich eingefügt.")