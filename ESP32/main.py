from MicroWebSrv2 import *
import machine
from machine import RTC
import esp32
import time
import network
import socket

#Init Real Time Clock for Logging
rtc = machine.RTC()

#WIFI-Credentials
WIFI_SSID = "TP-Link_58E8"
WIFI_PWD = "15473202"

if __name__ == "__main__":
    #Init the WebServer and bind IP-Address and Port
    mws2 = MicroWebSrv2()
    mws2.SetEmbeddedConfig()
    mws2.DisableSSL()
    mws2.BindAddress = ("127.0.0.1",80)
    mws2.StartManaged()
    
    #Init WIFI-Connection
    try:
        wifi = network.WLAN(network.STA_IF) # use Station Mode
        wifi.active(True)
        wifi.config(dhcp_hostname = "ESP32-Sensor")
        wifi.connect(WIFI_SSID, WIFI_PWD)
        timestamp = (str(rtc.datetime()[0])+"."+str(rtc.datetime()[1])+"."+str(rtc.datetime()[2])+" "+str(rtc.datetime()[4])+":"+str(rtc.datetime()[5])+":"+str(rtc.datetime()[6]))
        mws2.Log("Timestamp: " + timestamp + ", Msg: WiFi-Connection active!", MicroWebSrv2.INFO)
    except Exception as e:
        timestamp = (str(rtc.datetime()[0])+"."+str(rtc.datetime()[1])+"."+str(rtc.datetime()[2])+" "+str(rtc.datetime()[4])+":"+str(rtc.datetime()[5])+":"+str(rtc.datetime()[6]))
        mws2.Log("Timestamp: " + timestamp + ", Msg: WiFi-Connection failed! Exception: " + e, MicroWebSrv2.ERROR)

    print(wifi.ifconfig()[0])

        #Endpoint for retrieving Env-Param's
    @WebRoute(GET, '/metrics')
    def getEnvironmentParameters(mws2, request):
        #Measured Environment Parameters getting logged onto the ESP32 Web-Server
        timestamp = (str(rtc.datetime()[0])+"."+str(rtc.datetime()[1])+"."+str(rtc.datetime()[2])+" "+str(rtc.datetime()[4])+":"+str(rtc.datetime()[5])+":"+str(rtc.datetime()[6]))
        esp_freq: float = machine.freq() / 1000000 #in MHz
        esp_temp: float = round((esp32.raw_temperature()-32)/1.8, 1) #From Fahrenheit to Celsius
        env_temp: float = 0
        env_humi: float = 0
        env_co2p: float = 0
        env_brig: float = 0

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
            mws2.Log("Timestamp: " + timestamp + ", Msg: Occured Exception: " + e, MicroWebSrv2.ERROR)
    
    @WebRoute(GET, '/test')
    def RequestTest(microWebSrv2, request) :
        request.Response.ReturnOkJSON({
            'ClientAddr' : request.UserAddress,
            'Accept'     : request.Accept,
            'UserAgent'  : request.UserAgent
        })
    
    while True:
        try:
            while not wifi.isconnected():
                mws2.Log("No WiFi-Connection!", MicroWebSrv2.WARNING)
            #Measured Environment Parameters getting logged onto the ESP32 Web-Server
            timestamp = (str(rtc.datetime()[0])+"."+str(rtc.datetime()[1])+"."+str(rtc.datetime()[2])+" "+str(rtc.datetime()[4])+":"+str(rtc.datetime()[5])+":"+str(rtc.datetime()[6]))
            esp_freq: float = machine.freq() / 1000000
            esp_temp: float = round((esp32.raw_temperature()-32)/1.8, 1)
            env_temp: float = 0
            env_humi: float = 0
            env_co2p: float = 0
            env_brig: float = 0
            
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
            mws2.Log("Timestamp: " + timestamp + ", Msg: Occured Exception: " + e, MicroWebSrv2.ERROR)


