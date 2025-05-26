# ESP32 Game Controller

This ESP32 firmware implements a wireless game controller that uses MQTT for communication with game clients. The controller supports automatic discovery and connection through a central server.

## Features

- **Automatic Discovery**: Connects to central MQTT server to discover available game clients
- **Dual Connection**: Uses central server for discovery, local connection for gaming
- **Button Support**: 4 configurable buttons with press/release detection
- **Joystick Support**: 2 analog joysticks with directional mapping
- **JSON Communication**: Uses JSON messages for structured data exchange
- **Connection Management**: Automatic reconnection and error handling

## Hardware Requirements

- ESP32 development board
- 4 Push buttons (connected to pins 23, 22, 21, 19)
- 2 Analog joysticks (connected to pins 15,4 and 13,12)
- Pull-up resistors for buttons (or use internal pull-ups)

## Software Requirements

### Arduino Libraries
- **WiFi** (ESP32 core library)
- **PubSubClient** (MQTT client library)
- **ArduinoJson** (JSON parsing and generation)

### Installation
1. Install ESP32 Arduino Core in Arduino IDE
2. Install required libraries through Library Manager:
   - PubSubClient by Nick O'Leary
   - ArduinoJson by Benoit Blanchon

## Configuration

### WiFi Settings
Update the following in the code:
```cpp
const char* ssid = "Your_WiFi_SSID";
const char* password = "Your_WiFi_Password";
```

### Central Server Settings
The central server settings are pre-configured:
```cpp
const char* central_mqtt_server = "31.44.2.222";
const int central_mqtt_port = 1883;
const char* central_mqtt_username = "kit";
const char* central_mqtt_password = "1234";
```

## Protocol Flow

1. **WiFi Connection**: Controller connects to WiFi network
2. **Central Server Discovery**: 
   - Connects to central MQTT server
   - Sends discovery request with unique device ID
   - Receives client IP and port information
3. **Local Connection**:
   - Connects to client's local MQTT broker
   - Registers and receives controller ID
   - Starts sending input data

## Message Format

### Discovery Request (to central server)
```json
{
  "action": "discover_client",
  "device_id": "ESP32-XXXX"
}
```

### Client Response (from central server)
```json
{
  "action": "client_info", 
  "device_id": "ESP32-XXXX",
  "ip": "192.168.1.100",
  "port": 1883,
  "client_id": "game_controller_client"
}
```

### Button Input (to local client)
```json
{
  "button": 1,
  "pressed": true
}
```

### Joystick Input (to local client)
```json
{
  "joystick": 1,
  "x": 512,
  "y": 300,
  "pressed": false
}
```

## Pin Configuration

| Component | Pin | Notes |
|-----------|-----|-------|
| Button 1 | 23 | INPUT_PULLUP |
| Button 2 | 22 | INPUT_PULLUP |
| Button 3 | 21 | INPUT_PULLUP |
| Button 4 | 19 | INPUT_PULLUP |
| Left Joystick X | 15 | Analog input |
| Left Joystick Y | 4 | Analog input |
| Right Joystick X | 13 | Analog input |
| Right Joystick Y | 12 | Analog input |

## Simulation Mode

The controller includes a simulation mode for testing without physical hardware. When real hardware is not connected, it will cycle through button presses automatically every 2 seconds. To switch to real hardware mode:

1. Comment out: `simulateInputs();`
2. Uncomment: `checkRealInputs();`

## Troubleshooting

- **WiFi Connection Issues**: Check SSID and password
- **Central Server Connection**: Verify server IP and credentials
- **Local Connection Timeout**: Ensure client application is running and firewall allows connections
- **No Input Response**: Check if controller is properly registered and connected to local client 