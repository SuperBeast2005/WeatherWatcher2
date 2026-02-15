import machine
import esp32
import network
import socket
import time
import json
import uasyncio as asyncio
import gc
from machine import RTC, Pin, SoftI2C, ADC
import ssd1306
import dht
import math

# --- WLAN-KONFIGURATION ---
WIFI_SSID = "esp32_wlan"
WIFI_PWD = "wlanesp32"
SERVER_PORT = 80

# --- RTC initialisieren ---
rtc = machine.RTC()

# DHT11 Sensor auf Pin 33
dht11 = dht.DHT11(Pin(33, Pin.IN))

# --- LDR ---
ldr = ADC(Pin(34, Pin.IN))
ldr.width(ADC.WIDTH_12BIT)
ldr.atten(ADC.ATTN_11DB)

# --- OLED-Pins ---
scl_pin = 25
sda_pin = 26
i2c = SoftI2C(scl=Pin(scl_pin), sda=Pin(sda_pin))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# --- HILFSFUNKTIONEN ---
def get_timestamp():
    t = rtc.datetime()
    return "{:04d}.{:02d}.{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[4], t[5], t[6])

def oled_metrics(metrics: dict):
    oled.fill(0)
    oled.text("ESPFreq:{}MHz".format(metrics["ESP_FREQ"]), 0, 0)
    oled.text("ESPTemp:{} C".format(metrics["ESP_TEMP"]), 0, 10)
    oled.text("Temp:   {} C".format(metrics["ENV_TEMP"]), 0, 20)
    oled.text("Humi:   {}%".format(metrics["ENV_HUMI"]), 0, 30)
    oled.text("eCO2:   {}%".format(metrics["ENV_CO2P"]), 0, 40)
    oled.text("Brig:   {}lx".format(metrics["ENV_BRIG"]), 0, 50) # Fix: Corrected key
    oled.show()

def read_lux(adc_value):
    # 1. Konstanten definieren
    GAMMA = 0.7          # Steilheit der Kennlinie
    RL10 = 50            # Widerstand bei 10 Lux in kOhm (typisch für GL5528)
    R_FIXED = 10         # Dein Festwiderstand in kOhm (10k)
    V_REF = 3.3          # Referenzspannung
    ADC_RES = 4095       # 12-Bit Auflösung

    # 2. Fehler vermeiden (Division durch Null)
    if adc_value <= 0: return 0
    if adc_value >= ADC_RES: adc_value = ADC_RES - 1

    # 3. Spannung berechnen
    voltage = adc_value / ADC_RES * V_REF
    
    # 4. Widerstand des LDR berechnen (Spannungsteiler-Formel umgestellt)
    # Formel: R_LDR = R_FIXED * (V_REF / V_OUT - 1)
    resistance = R_FIXED * (V_REF / voltage - 1)

    # 5. Lux berechnen
    # Formel umgestellt: Lux = 10 * (RL10 / resistance)^(1/GAMMA)
    lux = math.pow(RL10 / resistance, 1 / GAMMA) * 10
    
    return round(lux, 1)

def create_metrics_json():
    try:
        dht11.measure()
        temp = dht11.temperature()
        humi = dht11.humidity()
    except:
        temp, humi = 0, 0

    return {
        "TIMESTAMP": get_timestamp(),
        "ESP_FREQ": machine.freq() // 1000000,
        "ESP_TEMP": round((esp32.raw_temperature() - 32) / 1.8, 1),
        "ENV_TEMP": temp,
        "ENV_HUMI": humi,
        "ENV_CO2P": 0, #(eco2 // 10000), # Platzhalter, da kein Sensor vorhanden 
        "ENV_BRIG": read_lux(ldr.read())
    }

def connect_wifi():
    """WLAN-Verbindung herstellen und IP zurückgeben."""
    print(">>> Starte WiFi Verbindung...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        wlan.config(pm=0)
    except:
        pass
    
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PWD)
        for _ in range(15):
            if wlan.isconnected(): break
            time.sleep(1)
    
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"VERBUNDEN! IP: {ip}")
        return ip
    return None

# --- ASYNC FUNKTIONEN ---
async def oled_curl_async(metrics: dict):
    """Zeigt kurzzeitig den Log-Eintrag an, ohne den Server zu blockieren."""
    oled.fill(0)
    oled.text("{}".format(metrics["TIMESTAMP"][11:19]), 0, 0)
    oled.text("GET /metrics", 0, 10)
    oled.text("erfolgreich!", 0, 20)
    oled.show()
    await asyncio.sleep(3) # Nicht-blockierendes Warten
    
async def handle_client(reader, writer):
    """Verarbeitet HTTP Anfragen asynchron."""
    try:
        request_line = await reader.readline()
        # Header konsumieren
        while await reader.readline() != b"\r\n":
            pass

        request = request_line.decode().strip()
        
        if "GET /metrics" in request:
            data = create_metrics_json()
            # Starte den Display-Log im Hintergrund
            asyncio.create_task(oled_curl_async(data))
            
            json_data = json.dumps(data)
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "Access-Control-Allow-Origin: *\r\n"
                "Connection: close\r\n\r\n"
                + json_data
            )
            writer.write(response.encode())
            
        elif "GET /healthcheck" in request:
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK")
        else:
            writer.write(b"HTTP/1.1 404 Not Found\r\n\r\nNot Found")

        await writer.drain()
        await writer.wait_closed()
    except Exception as e:
        print(f"Request Error: {e}")
    finally:
        gc.collect()

async def display_updater():
    """Aktualisiert das Display alle 2 Sekunden, sofern kein Log aktiv ist."""
    while True:
        # Nur Metriken zeigen, wenn keine curl-Meldung das Display blockiert
        # (Da create_task für oled_curl_async genutzt wird, überschreiben wir hier einfach)
        data = create_metrics_json()
        oled_metrics(data)
        await asyncio.sleep(2)

async def main():
    ip = connect_wifi()
    if not ip:
        print("Kritischer Fehler: Kein Netzwerk. Neustart...")
        await asyncio.sleep(10)
        machine.reset()

    # Server starten
    print(f">>> Server läuft auf http://{ip}/metrics")
    server = asyncio.start_server(handle_client, "0.0.0.0", SERVER_PORT)
    
    # Aufgaben parallel ausführen
    await asyncio.gather(server, display_updater())

# --- AUSFÜHREN ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server gestoppt.")

