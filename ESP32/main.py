import machine
import esp32
import network
import socket
import time
import json
from machine import RTC, Pin, SoftI2C
import ssd1306

# HIER MIT EIGENEM WLAN KONFIGURIEREN
WIFI_SSID = "iPhone von A"
WIFI_PWD  = "wehweh123"
SERVER_PORT = 80

# RTC initialisieren
rtc = machine.RTC()

# OLED-Pins
scl_pin = 25
sda_pin = 26

# initialize I2C bus (software mode)
i2c = SoftI2C(scl = Pin(scl_pin), sda = Pin(sda_pin))

# initialize oled display on standard address
display_width = 128
display_height = 64
oled = ssd1306.SSD1306_I2C(display_width, display_height, i2c)

def oled_metrics(metrics: dict):
    """Zeigt die wichtigsten Metriken auf dem OLED an."""
    oled.fill(0) # Bildschirm löschen
    oled.text("ESPFreq:{}MHz".format(metrics["ESP_FREQ"]), 0, 0)
    oled.text("ESPTemp:{}C".format(metrics["ESP_TEMP"]), 0, 10)
    oled.text("Temp:   {}C".format(metrics["ENV_TEMP"]), 0, 20)
    oled.text("Humi:   {}%".format(metrics["ENV_HUMI"]), 0, 30)
    oled.text("CO2:    {}%".format(metrics["ENV_CO2P"]), 0, 40)
    oled.text("Brig:   {}Lux".format(metrics["ENV_CO2P"]), 0, 50)
    oled.show()

def oled_curl(metrics: dict):
    oled.fill(0) # Bildschirm löschen
    oled.text("{}".format(metrics["TIMESTAMP"][11:19]), 0, 0)
    oled.text("GET /metrics", 0, 10)
    oled.text("erfolgreich!", 0, 20)
    oled.show()
    time.sleep(5)

def get_timestamp():
    """Erstellt einen formatierten Zeitstempel."""
    t = rtc.datetime()
    # Format: YYYY.MM.DD HH:MM:SS
    return "{:04d}.{:02d}.{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[4], t[5], t[6])

def connect_wifi():
    """Verbindet mit WiFi und deaktiviert den Energiesparmodus."""
    print(">>> Starte WiFi Verbindung...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    try:
        wlan.config(pm=0)
        print(">> WLAN-Power-Management deaktiviert (pm=0) -> Maximale Leistung.")
    except Exception as e:
        print(f">> Warnung beim Setzen von pm=0: {e}")     # Deaktiviert den WiFi-Energiesparmodus (pm=0), verhindert hohe Latenzen und Timeouts.

    wlan.config(dhcp_hostname="ESP32-Sensor")
    
    if not wlan.isconnected():
        print(f"Verbinde mit {WIFI_SSID}...")
        wlan.connect(WIFI_SSID, WIFI_PWD)

        # Warten mit Timeout (max 15 sek)
        for i in range(15):
            if wlan.isconnected():
                break
            time.sleep(1)
            print(".", end="")
        print("")

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"VERBUNDEN! IP: {ip}")
        return ip
    else:
        print("FEHLER: Keine WLAN-Verbindung möglich.")
        return None

def create_metrics_json():
    """Liest Sensoren und erstellt das JSON-Objekt."""
    timestamp = get_timestamp()
    esp_freq = machine.freq() / 1000000 # MHz
    
    try:
        # Interne Temperatur (nicht auf allen ESP32 genau kalibriert)
        esp_temp = round((esp32.raw_temperature() - 32) / 1.8, 1)
    except:
        esp_temp = 0.0

    # Hier später echte Sensordaten einfügen
    data = {
        "TIMESTAMP": timestamp,
        "ESP_FREQ": esp_freq,
        "ESP_TEMP": esp_temp,
        "ENV_TEMP": 0,
        "ENV_HUMI": 0,
        "ENV_CO2P": 0,
        "ENV_BRIG": 0
    }
    return data

if __name__ == "__main__":
    
    # 1. Mit WiFi verbinden
    ip = connect_wifi()
    if not ip:
        print("Kritischer Fehler: Kein Netzwerk. Neustart in 10s...")
        time.sleep(10)
        machine.reset()

    # 2. Socket Server vorbereiten
    try:
        # Socket erstellen
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Erlaubt den sofortigen Neustart des Ports, falls der Server crasht
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Binden an IP und Port
        s.bind(('', SERVER_PORT))
        s.listen(5) # Max 5 Wartende Verbindungen
        print(f">>> Server bereit auf: http://{ip}/metrics")
        print(">>> Drücke Strg+C zum Beenden.")
        
    except OSError as e:
        print(f"Fehler beim Starten des Sockets: {e}")
        machine.reset()

    # 3. Endlosschleife für Anfragen
    while True:
        try:
            #Display mit Metriken starten
            oled_metrics(create_metrics_json())
            
            # Auf Verbindung warten (blockiert, bis jemand anfragt)
            conn, addr = s.accept()
            
            # Timeout setzen, falls Client nichts sendet
            conn.settimeout(2.0)
            
            # Anfrage empfangen (wir lesen nur die ersten 1024 Bytes, das reicht für die URL)
            request = conn.recv(1024)
            request_str = str(request)
            
            # Routing
            if "GET /metrics" in request_str:
                raw_data = create_metrics_json()
                oled_curl(raw_data) #Anfrage aufm OLED-Display Loggen
                # Metriken senden
                json_data = json.dumps(raw_data)
                response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json\r\n"
                    "Connection: close\r\n"
                    "Access-Control-Allow-Origin: *\r\n" # Erlaubt Zugriff von anderen Webseiten
                    "\r\n"
                    + json_data
                )
                conn.send(response.encode())
                # Optional: Kurzes Log
                # print(f"Metriken gesendet an {addr[0]}")
                
            elif "GET /healthcheck" in request_str:
                # Test-Seite
                conn.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nHealthcheck OK")
                
            else:
                # 404 Fehlerseite
                conn.send(b"HTTP/1.1 404 Not Found\r\n\r\nNot Found")

            # Verbindung sauber schließen
            conn.close()

        except OSError as e:
            # Fehler (z.B. Timeout) abfangen, damit der Server nicht abstürzt
            conn.close()
            
        except Exception as e:
            print(f"Server-Fehler: {e}")
            # Bei kritischen Fehlern kurz warten
            time.sleep(1)



