from machine import I2C
import time

class CCS811:
    def __init__(self, i2c, addr=90):
        self.i2c = i2c
        self.addr = addr
        
        # Prüfen, ob der Sensor da ist
        if self.i2c.scan().count(addr) == 0:
            raise RuntimeError("CCS811 nicht gefunden")

        # Hardware-ID prüfen (sollte 0x81 sein)
        if self.i2c.readfrom_mem(self.addr, 0x20, 1)[0] != 0x81:
            raise RuntimeError("Falsche Device-ID")

        # App-Start (Schreibe auf Boot-Register)
        self.i2c.writeto(self.addr, b'\xF4')
        time.sleep(0.1)

        # Drive Mode: 1 Sekunde Intervall (0x01 << 4)
        self.i2c.writeto_mem(self.addr, 0x01, b'\x10')

    def data_ready(self):
        status = self.i2c.readfrom_mem(self.addr, 0x00, 1)[0]
        return status & 0x08

    def read_data(self):
        if not self.data_ready():
            return None, None
        
        # Lese 4 Bytes: eCO2 (high, low) und TVOC (high, low)
        data = self.i2c.readfrom_mem(self.addr, 0x02, 4)
        eco2 = (data[0] << 8) | data[1]
        tvoc = (data[2] << 8) | data[3]
        return eco2, tvoc