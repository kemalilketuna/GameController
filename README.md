# Bat Controller

A project that allows ESP32-based bat-shaped controllers to send button and joystick inputs to a computer via MQTT, which are then converted to keyboard keypresses.

## Project Structure

The project consists of two main parts:

1. **ESP32 Controller** - Located in the `Controller` folder
   - Reads button and joystick inputs
   - Communicates with the computer via MQTT
   - Each controller gets a unique ID from the client

2. **Python Client** - Located in the `Client` folder
   - Receives controller inputs via MQTT
   - Converts inputs to keyboard keypresses
   - Provides a GUI for mapping controller buttons to keyboard keys
   - Supports multiple controllers simultaneously

## Setup Instructions

### ESP32 Controller

1. Flash the `Controller/esp32_controller.ino` file to your ESP32 using the Arduino IDE
2. Connect 4 buttons and 2 joysticks to the ESP32 according to the pin definitions in the code
3. Make sure your ESP32 is connected to the same network as your computer

### Python Client

#### Windows Setup
```
cd Client
pip install -r requirements.txt
python main.py
```

#### macOS Setup
```
cd Client
pip install -r requirements.txt
python main.py
```

## MQTT Setup

The project uses MQTT for communication between the controllers and the client.

1. Install an MQTT broker on your computer or use a cloud-based broker
2. Update the MQTT server settings in both the ESP32 code and the Python client
3. Default MQTT settings:
   - Server: 192.168.0.23
   - Port: 1883

## Using the Client

1. Launch the Python client
2. Power on your bat controller(s)
3. The controllers should automatically register with the client
4. Select a controller from the list and click "Configure"
5. Map controller buttons and joystick directions to keyboard keys
6. Save your mappings
7. Enjoy playing games with your custom bat controller!

## License

This project is open-source. Feel free to modify and distribute it as needed.

