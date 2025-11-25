from MicroWebSrv2 import *
import machine
from machine import RTC
import esp32
import time
import network
import socket

#Init Real Time Clock for Logging
rtc = machine.RTC()

#Init the WebServer and a managed Pool and bind IP-Address
mws2 = MicroWebSrv2()
mws2.SetEmbeddedConfig()
mws2.StartManaged()

#WIFI-Credentials
WIFI_SSID = "TP-Link_58E8"
WIFI_PWD = "15473202"

#Init WIFI-Connection
wifi = network.WLAN(network.STA_IF) # use Station Mode
wifi.active(True)
wifi.config(dhcp_hostname = "ESP32-Sensor")
wifi.connect(WIFI_SSID, WIFI_PWD)
mws2.Log("WiFi-Connection active!", MicroWebSrv2.INFO)

#Endpoint for retrieving Env-Param's
@WebRoute(GET, '/')
def getEnvironmentParameters(mws2, request):
    #Measured Environment Parameters getting logged onto the ESP32 Web-Server
    timestamp = (str(rtc.datetime()[0])+"."+str(rtc.datetime()[1])+"."+str(rtc.datetime()[2])+" "+str(rtc.datetime()[4])+":"+str(rtc.datetime()[5])+":"+str(rtc.datetime()[6]))
    esp_freq = str(machine.freq() / 1000000) + " MHz"
    esp_temp = str(round((esp32.raw_temperature()-32)/1.8, 1)) + " Celsius"
    env_temp = ""
    env_humi = ""
    env_co2p = ""
    env_brig = ""
    
    #Dictionary, which represents a JSON
    data = {
        "TIMESTAMP": timestamp,
        "ESP_FREQ": esp_freq,
        "ESP_TEMP": esp_temp,
        "ENV_TEMP": env_temp,
        "ENV_HUMI": env_humi,
        "ENV_CO2P": env_co2p,
        "ENV_BRIG": env_brig
    }
    try:
        #Returns Data-Dictionary as a JSON-Object
        request.ReturnOkJSON(data)
        mws2.Log("Timestamp: " + timestamp + ", Msg: Successfully retrieved real-time data from the ESP32 Environment Parameters Endpoint!")
        
    except Exception as e:
        request.ResponseReturnJSON(500, {"error": "internal error"})
        mws2.Log("Occured Exception: " + e, MicroWebSrv2.WARNING)

if __name__ == "__main__":
    print(wifi.ifconfig()[0])
    while True:
        try:
            while not wifi.isconnected():
                mws2.Log("No WiFi-Connection!", MicroWebSrv2.WARNING)
            #Measured Environment Parameters getting logged onto the ESP32 Web-Server
            timestamp = (str(rtc.datetime()[0])+"."+str(rtc.datetime()[1])+"."+str(rtc.datetime()[2])+" "+str(rtc.datetime()[4])+":"+str(rtc.datetime()[5])+":"+str(rtc.datetime()[6]))
            esp_freq = str(machine.freq() / 1000000) + " MHz"
            esp_temp = str(round((esp32.raw_temperature()-32)/1.8, 1)) + " Celsius"
            env_temp = ""
            env_humi = ""
            env_co2p = ""
            env_brig = ""
            
            #Dictionary, which represents a JSON
            data = {
                "TIMESTAMP": timestamp,
                "ESP_FREQ": esp_freq,
                "ESP_TEMP": esp_temp,
                "ENV_TEMP": env_temp,
                "ENV_HUMI": env_humi,
                "ENV_CO2P": env_co2p,
                "ENV_BRIG": env_brig
            }
            logs = mws2.Log(data, MicroWebSrv2.INFO)
            time.sleep_ms(1000)
            
        except Exception as e:
            mws2.Log("Occured Exception: " + e, MicroWebSrv2.WARNING)
else:
    #Close WIFI-Connection and stop Web-Server
    wifi.disconnect()
    mws2.Stop()