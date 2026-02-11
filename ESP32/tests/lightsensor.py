from machine import Pin, ADC, PWM
from time import sleep

# analog input pin
ldr = ADC(Pin(27 , Pin.IN))
ldr.atten(ADC.ATTN_11DB) # voltage range: 0.15-2.45 V

while True:
    # measure voltage at sensor pin (ldr is a variable resistor)
    brightness = ldr.read()
    print(brightness)
    
    sleep(1)
    
    
