"""
Game Controller Client
---------------------
This is the main entry point for the Game Controller Client application.
It connects to game controllers via MQTT and maps their inputs to keyboard events.
"""

import os
import importlib.util

# Ensure we're in the correct directory (Client directory)
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Import from gui.py in the current directory
gui_path = os.path.join(script_dir, "gui.py")
spec = importlib.util.spec_from_file_location("gui_module", gui_path)
gui_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui_module)
GameControllerGUI = gui_module.GameControllerGUI
from mqtt.client import (
    create_central_mqtt_client,
    create_local_mqtt_client,
    connect_to_central_mqtt,
    connect_to_local_mqtt,
    cleanup_mqtt,
    cleanup_controllers,
    controllers,
    set_log_callback,
    is_mosquitto_running,
)
from config.settings import SettingsManager


def main():
    """Main entry point for the application"""
    # Initialize settings manager
    settings_manager = SettingsManager()

    # Create the GUI
    app = GameControllerGUI(controllers, settings_manager)

    # Set up logging callback
    set_log_callback(app.add_log_message)

    # Set up MQTT clients
    central_client = create_central_mqtt_client()
    local_client = create_local_mqtt_client(userdata=app)

    # Store MQTT clients in app
    app.central_mqtt_client = central_client
    app.local_mqtt_client = local_client

    # Connect to central MQTT server for device discovery
    central_connected = connect_to_central_mqtt(central_client)
    if central_connected:
        print("Connected to central MQTT server for device discovery")
        app.update_central_mqtt_status(True)
    else:
        print("Failed to connect to central MQTT server")
        app.update_central_mqtt_status(False)

    # Only try to connect to local MQTT if Mosquitto is actually running
    if is_mosquitto_running():
        local_connected = connect_to_local_mqtt(local_client)
        if local_connected:
            print("Connected to local MQTT server")
            app.update_mqtt_status(True)
        else:
            print("Failed to connect to local MQTT server")
            app.update_mqtt_status(False)
    else:
        print("Local Mosquitto not running")
        app.update_mqtt_status(False)

    # Start the GUI
    app.mainloop()

    # Clean up
    cleanup_mqtt(central_client)
    cleanup_mqtt(local_client)
    cleanup_controllers()


if __name__ == "__main__":
    main()
