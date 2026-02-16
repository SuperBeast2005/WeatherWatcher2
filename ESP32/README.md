# Weather Watcher - ESP-Interface

ESP32 web server equipped with sensors, featuring a GET endpoint to extract sensor data.

## Setup

### 1. Replicate the ESP32 as depicted:

![component flowchart](Documentation/images/circuit.png) 

### 2. Flash Micropython onto the ESP32 via Thonny IDE

Follow this Tutorial: https://randomnerdtutorials.com/getting-started-thonny-micropython-python-ide-esp32-esp8266/ 

### 3. Save main.py and libs onto the ESP32

1. Connect the ESP32 to your computer via USB
2. Open Thonny (or a similar IDE), the ESP32 should be automatically detected after flashing and will attempt to execute main.py (nothing will happen if main.py is empty).
3. Copy main.py from the repository, paste it into a new file in Thonny, and save it on the ESP32 as main.py (follow the same process for the libraries).

### IMPORTANT!!!

Completed source code on the ESP32 is only stored locally on the ESP32!
To track changes, clone the repo in VS Code or similar, and overwrite the main.py in the repo with the ESP32's main.py whenever new changes are made!
Similarly, save new libraries under the directory WeatherWatcher/ESP32/libs.
