from machine import Pin, SoftI2C
import ssd1306
import sht3x
from time import sleep

scl_pin = 25
sda_pin = 26

# initialize I2C bus (software mode)
i2c = SoftI2C(scl = Pin(scl_pin), sda = Pin(sda_pin))
i2c.scan() # list all devices on bus

# initialize oled display on standard address
display_width = 128
display_height = 64
oled = ssd1306.SSD1306_I2C(display_width, display_height, i2c)

while True:
    oled.fill(0) # blank display
    oled.text("Hello I2C world!", 0, 0)
    oled.text("...", 0, 20)
    oled.show()
    
    oled.fill(0)
    oled.text("Hello I2C world!", 0, 0)
    # this is an ugly but fast way to round a number to two decimals
    oled.text("Temp.: C", 0, 20)
    oled.text("Hum.: %", 0, 30)
    oled.show()
    
    # show a nice animation instead of sleep(10)
    for i in range(1, 11):
        dots = "." * i
        oled.text(dots, 0, 50)
        oled.show()
        sleep(1)
