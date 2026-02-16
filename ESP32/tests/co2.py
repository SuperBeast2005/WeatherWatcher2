from machine import Pin, I2C
from ccs811 import CCS811
import time

# I2C Initialisierung (Pins je nach Board anpassen)
# ESP32 Beispiel: SDA=21, SCL=22
i2c = I2C(0, scl=Pin(35), sda=Pin(34), freq=100000)
print(i2c.scan())
sensor = CCS811(i2c)

print("Warte auf Sensor-Daten...")

while True:
    eco2, tvoc = sensor.read_data()
    
    if eco2 is not None:
        print(f"eCO2: {eco2} ppm, TVOC: {tvoc} ppb")
    else:
        print("Keine neuen Daten.")
        
    time.sleep(2)