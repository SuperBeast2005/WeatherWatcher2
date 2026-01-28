import machine
import esp32
import network
import socket
import time
import json
from machine import RTC
from machine import Pin
import dht

# HIER MIT EIGENEM WLAN KONFIGURIEREN
WIFI_SSID = "iPhone von A"
WIFI_PWD  = "wehweh123"
SERVER_PORT = 80

# RTC initialisieren
rtc = machine.RTC()

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
        dht11 = dht.DHT11(Pin(33, Pin.IN))
        sensor = dht11.measure()
        
        # Interne Temperatur (nicht auf allen ESP32 genau kalibriert)
        esp_temp = round((esp32.raw_temperature() - 32) / 1.8, 1)
        env_temp = sensor.temperature()
        env_humi = sensor.humidity()
        
        # Sekunde warten zur Sicherheit
        time.sleep(1)
        
    except Exception as e:
        esp_temp = 0.0
        print("FEHLER: " + e)

    # Hier später echte Sensordaten einfügen
    data = {
        "TIMESTAMP": timestamp,
        "ESP_FREQ": esp_freq,
        "ESP_TEMP": esp_temp,
        "ENV_TEMP": env_temp,
        "ENV_HUMI": env_humi,
        "ENV_CO2P": 0,
        "ENV_BRIG": 0
    }
    return json.dumps(data)

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
            # Auf Verbindung warten (blockiert, bis jemand anfragt)
            conn, addr = s.accept()
            
            # Timeout setzen, falls Client nichts sendet
            conn.settimeout(2.0)
            
            # Anfrage empfangen (wir lesen nur die ersten 1024 Bytes, das reicht für die URL)
            request = conn.recv(1024)
            request_str = str(request)
            
            # Routing
            if "GET /metrics" in request_str:
                # Metriken senden
                json_data = create_metrics_json()
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


