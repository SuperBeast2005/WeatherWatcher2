from machine import Pin, SoftI2C
import ssd1306
from time import sleep
import dht

# --- Setup ---
dht11 = dht.DHT11(Pin(33, Pin.IN))

sck_pin = 25
sda_pin = 26

i2c = SoftI2C(scl=Pin(sck_pin), sda=Pin(sda_pin))

display_width = 128
display_height = 64
oled = ssd1306.SSD1306_I2C(display_width, display_height, i2c)

# Zähler für das "Lebenszeichen"
counter = 0

print("Starte Loop...")

while True:
    try:
        # Versuche zu messen
        dht11.measure()
        
        # Werte holen
        temperature = dht11.temperature()
        humidity = dht11.humidity()
        
        # --- Display Ausgabe ---
        oled.fill(0) # Display leeren
        
        oled.text("STATUS: RUNNING", 0, 0)
        
        # Werte anzeigen
        oled.text("Temp: " + str(temperature) + " C", 0, 20)
        oled.text("Hum:  " + str(humidity) + " %", 0, 35)
        
        # --- Lebenszeichen (Blinkender Punkt) ---
        # Damit siehst du, dass der Loop noch läuft, 
        # auch wenn Temperatur gleich bleibt.
        if counter % 2 == 0:
            oled.text("*", 110, 0) # Sternchen oben rechts
        
        oled.show()
        
        # Debugging in der Konsole unten (optional)
        print("Messung OK:", temperature, humidity)

    except OSError as e:
        # WICHTIG: Wenn der Sensor spinnt, stürzt das Programm nicht ab,
        # sondern zeigt "Fehler" an und probiert es gleich nochmal.
        print("Sensor Fehler (OSError)")
        oled.fill(0)
        oled.text("Sensor Fehler!", 0, 25)
        oled.text("Versuche neu...", 0, 40)
        oled.show()
    
    except Exception as e:
        print("Anderer Fehler:", e)

    # Zähler erhöhen
    counter += 1
    
    # Warte 2 Sekunden (DHT11 braucht Zeit zum Erholen)
    sleep(2)
