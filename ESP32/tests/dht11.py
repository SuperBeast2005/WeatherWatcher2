from machine import Pin
from time import sleep
import dht

# custom one-wire communication protocol
dht11 = dht.DHT11(Pin(33, Pin.IN))

while True:
    dht11.measure()
    sleep(1)
    temperature = dht11.temperature() # temperature in °C
    humidity = dht11.humidity() # rel. humidity
    
    print("Temperature:\t" + str(temperature) + "°C")
    print("Humidity:\t" + str(humidity) + "%")