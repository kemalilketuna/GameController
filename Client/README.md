# Game Controller Client

This application allows ESP32-based game controllers to connect via MQTT and maps their inputs to keyboard events. The system uses a central server for device discovery and a local MQTT broker for game input communication.

## Features

- **Central Server Discovery**: Controllers connect to a central MQTT server to discover available clients
- **Local Communication**: After discovery, controllers connect directly to the client's local MQTT broker for low-latency gaming
- **Key Mapping**: Customizable key mappings with persistence and default configuration
- **Activity Logging**: Real-time logging of controller inputs and system events
- **Multiple Controllers**: Support for multiple controllers with individual configurations

## Project Structure

The project has been restructured into the following packages:

- **controller/** - Contains the game controller logic and mappings
- **gui/** - Contains all the GUI components, split into separate modules
- **mqtt/** - Contains the MQTT client and messaging logic (both central and local)
- **config/** - Contains configuration management and settings persistence
- **utils/** - Contains utility functions like keyboard handling

## How to Run

1. **Install Requirements**:
   ```
   pip install -r requirements.txt
   ```

2. **Ensure Mosquitto is Available**: Make sure Mosquitto MQTT broker is installed and available in your system PATH.

3. **Run the Application**:
   ```
   python main.py
   ```

## System Architecture

1. **ESP32 Controller**: Connects to the central MQTT server (31.44.2.222) for discovery
2. **Central Server**: Facilitates discovery between controllers and clients
3. **Client Application**: 
   - Listens on central server for controller discovery requests
   - Starts local Mosquitto broker automatically when needed
   - Responds with local IP and port information
4. **Local Communication**: Controllers connect to client's local Mosquitto for game input

## Configuration

- **Default Key Mappings**: Stored in `config/default_mappings.json`
- **Controller Mappings**: Individual controller configs in `config/controller_X.json`
- **Mosquitto Settings**: Local broker configuration in `config/mosquitto_settings.json`

## Usage

1. Start the client application
2. The application automatically connects to the central server for discovery
3. Power on your ESP32 controller - it will automatically discover and connect
4. Configure key mappings using the GUI
5. Use "Save Mappings" to persist your configuration
6. Monitor activity in the "Logs" tab

## Switching to the New Structure

If you're migrating from the old monolithic structure to the new modular structure:

1. Run the test script first to verify imports work correctly:
   ```
   python test_restructured.py
   ```

2. If the test passes, rename the files to switch over:
   ```
   ren main.py main.py.bak
   ren main_final.py main.py
   ```

3. After confirming the new structure works, you can remove the old files:
   - keyboard_mac.py (moved to utils/keyboard_mac.py)
   - keyboard_win.py (moved to utils/keyboard_win.py)
   - main.py.bak (backup of the original main.py)
   - main_new.py (intermediate version)

## Requirements

- Python 3.6+
- Mosquitto MQTT broker
- Required Python packages (listed in requirements.txt)
