import dht
from machine import Pin, ADC, PWM
from time import sleep

# analog input pin
ldr = ADC(Pin(34 , Pin.IN))
ldr.atten(ADC.ATTN_11DB) # voltage range: 0.15-2.45 V

# custom one-wire communication protocol
dht11 = dht.DHT11(Pin(33, Pin.IN))

while True:
    dht11.measure() # measure dht11 metrics
    brightness = ldr.read() # measure voltage at sensor pin (ldr is a variable resistor)
    
    sleep(1)
    
    temperature = dht11.temperature() # temperature in °C
    humidity = dht11.humidity() # rel. humidity
    
    print("Brightness:\t" + str(brightness))
    print("Temperature:\t" + str(temperature) + "°C")
    print("Humidity:\t" + str(humidity) + "%")
