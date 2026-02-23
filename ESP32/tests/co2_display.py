from machine import Pin, SoftI2C
import ssd1306
from time import sleep
# Falls deine Library anders heißt (z.B. ccs811_lib), hier anpassen
from ccs811 import CCS811 

# Pins definieren
scl_pin = 25
sda_pin = 26

# I2C Bus initialisieren
i2c = SoftI2C(scl=Pin(scl_pin), sda=Pin(sda_pin))

# Display initialisieren (128x64)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# Sensor initialisieren
# Wichtig: WAKE Pin des CCS811 muss auf GND liegen!
sensor = CCS811(i2c)

def update_display(co2, tvoc):
    oled.fill(0) # Display leeren
    
    # Header
    oled.text("CCS811 SENSOR", 10, 0)
    oled.text("----------------", 0, 10) # Einfacher Ersatz für hline
    
    # Messwerte
    oled.text("eCO2:", 0, 25)
    oled.text(f"{co2} ppm", 50, 25)
    
    oled.text("TVOC:", 0, 45)
    oled.text(f"{tvoc} ppb", 50, 45)
    
    oled.show()

print("Starte Messung...")

while True:
    try:
        # Je nach Library heißt die Methode .data_ready() oder .available()
        # Falls deine Lib keine Prüfung hat, kannst du die if-Abfrage auch weglassen
        if hasattr(sensor, 'data_ready') and sensor.data_ready():
            # Falls .get_data() nicht geht, probier .eco2 und .tvoc Eigenschaften
            eco2, tvoc = sensor.read_data() 
            update_display(eco2, tvoc)
        else:
            # Manche Libs lesen direkt aus
            eco2, tvoc = sensor.read_data()
            update_display(eco2, tvoc)
            
    except Exception as e:
        oled.fill(0)
        oled.text("Fehler:", 0, 0)
        # Wir kürzen den Fehlertext, damit er aufs Display passt
        oled.text(str(e)[:15], 0, 20) 
        oled.show()
        print("Sensor Fehler:", e)

    sleep(2) # CCS811 braucht im Standard-Modus 1-2 Sek. für neue Werte
