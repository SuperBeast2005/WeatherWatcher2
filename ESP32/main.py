import machine
import esp32
import network
import socket
import time
import json
import uasyncio as asyncio
import gc
import urequests as requests  # Erforderlich für Cloud-Upload
from machine import RTC, Pin, SoftI2C, ADC
import ssd1306
import dht
import math
import ubinascii
from ccs811 import CCS811

# --- KONFIGURATION ---
WIFI_SSID = "esp32_wlan"
WIFI_PWD = "wlanesp32"
SERVER_PORT = 80

# DWEET.ME KONFIGURATION
UNIQUE_ID = ubinascii.hexlify(machine.unique_id()).decode()
THING_NAME = "ESP32_Environment_{}".format(UNIQUE_ID[:6])

# --- RTC initialisieren ---
rtc = machine.RTC()

# --- SENSOREN SETUP ---
dht11 = dht.DHT11(Pin(33, Pin.IN))
ldr = ADC(Pin(34, Pin.IN))
ldr.width(ADC.WIDTH_12BIT)
ldr.atten(ADC.ATTN_11DB)

# I2C & Display
scl_pin = 25
sda_pin = 26
i2c = SoftI2C(scl=Pin(scl_pin), sda=Pin(sda_pin))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# CCS811 (CO2)
try:
    sensor = CCS811(i2c)
except Exception as e:
    print("CCS811 nicht gefunden:", e)
    sensor = None

# --- HILFSFUNKTIONEN ---
def urlencode(params):
    parts = []
    for k, v in params.items():
        # Ersetze Leerzeichen durch %20 für die URL-Konformität
        val = str(v).replace(" ", "%20").replace(":", "%3A")
        parts.append("{}={}".format(k, val))
    return "?" + "&".join(parts)

def get_timestamp():
    t = rtc.datetime()
    return "{:04d}.{:02d}.{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[4], t[5], t[6])

def read_lux(adc_value):
    GAMMA, RL10, R_FIXED, V_REF, ADC_RES = 0.7, 50, 10, 3.3, 4095
    if adc_value <= 0: return 0
    if adc_value >= ADC_RES: adc_value = ADC_RES - 1
    voltage = adc_value / ADC_RES * V_REF
    resistance = R_FIXED * (V_REF / voltage - 1)
    lux = math.pow(RL10 / resistance, 1 / GAMMA) * 10
    return round(lux, 1)

def create_metrics_json():
    try:
        dht11.measure()
        temp = dht11.temperature()
        humi = dht11.humidity()
        brig = ldr.read()
        eco2 = 0
        if sensor:
            eco2, _ = sensor.read_data()
    except:
        temp, humi, brig, eco2 = 0, 0, 0, 0

    return {
        "TIMESTAMP": get_timestamp(),
        "ESP_HWID": UNIQUE_ID,
        "ESP_FREQ": machine.freq() // 1000000,
        "ESP_TEMP": round((esp32.raw_temperature() - 32) / 1.8, 1),
        "ENV_TEMP": temp,
        "ENV_HUMI": humi,
        "ENV_CO2P": eco2,
        "ENV_BRIG": read_lux(brig)
    }

def oled_metrics(metrics: dict):
    oled.fill(0)
    oled.text("Cloud: {}".format(THING_NAME[-6:]), 0, 0) # Zeigt Teil der ID
    oled.text("Temp:  {}C".format(metrics["ENV_TEMP"]), 0, 10)
    oled.text("Humi:  {}%".format(metrics["ENV_HUMI"]), 0, 20)
    oled.text("eCO2:  {}ppm".format(metrics["ENV_CO2P"]), 0, 30)
    oled.text("Brig:  {}lx".format(metrics["ENV_BRIG"]), 0, 40)
    oled.show()

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Verbinde mit WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PWD)
        for _ in range(15):
            if wlan.isconnected(): break
            time.sleep(1)
    
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"Verbunden! IP: {ip}, DNS: {wlan.ifconfig()[3]}")
        return ip
    return None

# --- ASYNC TASKS ---
async def dweet_publisher():
    """Sendet die Sensordaten per GET-Request an die URL-Parameter."""
    # Basis-URL
    base_url = "http://dweet.me:3333/publish/yoink/for/{}".format(THING_NAME)
    
    while True:
        gc.collect()
        try:
            # 1. Daten generieren
            data = create_metrics_json()
            
            # 2. Daten in URL-Parameter umwandeln (?temp=20&humi=50...)
            params = urlencode(data)
            full_url = base_url + params
            
            print(f">>> Sende an: {full_url}")
            
            # 3. WICHTIG: Nutze .get() statt .post()
            res = requests.get(full_url)
            
            # Debugging
            print(f">>> Status: {res.status_code}")
            print(f">>> Server Antwort: {res.text}")
            
            res.close()
            print(">>> Daten erfolgreich übertragen!")
            
        except Exception as e:
            print("Dweet.me Fehler:", e)
        
        await asyncio.sleep(10)

async def handle_client(reader, writer):
    """Verarbeitet lokale HTTP Anfragen (z.B. für Monitoring im selben WLAN)."""
    try:
        request_line = await reader.readline()
        while await reader.readline() != b"\r\n": pass
        
        request = request_line.decode().strip()
        if "GET /metrics" in request:
            data = create_metrics_json()
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + json.dumps(data)
            writer.write(response.encode())
        else:
            writer.write(b"HTTP/1.1 404 Not Found\r\n\r\n")
        
        await writer.drain()
        await writer.wait_closed()
    except Exception as e:
        print("Server Fehler:", e)
    finally:
        gc.collect()

async def display_updater():
    """Aktualisiert das OLED alle 2 Sekunden."""
    while True:
        data = create_metrics_json()
        oled_metrics(data)
        await asyncio.sleep(2)

async def main():
    ip = connect_wifi()
    if not ip:
        print("Kein WiFi. Neustart in 10s...")
        await asyncio.sleep(10)
        machine.reset()

    # Lokaler Server & Cloud Tasks
    server = asyncio.start_server(handle_client, "0.0.0.0", SERVER_PORT)
    
    print("-" * 30)
    print(f"LOKAL:  http://{ip}/metrics")
    print(f"REMOTE: http://dweet.me:3333/publish/yoink/for/{THING_NAME}")
    print("-" * 30)

    await asyncio.gather(
        server, 
        display_updater(),
        dweet_publisher()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Beendet.")
