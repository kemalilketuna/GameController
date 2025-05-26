import paho.mqtt.client as mqtt
import json
import threading
import socket
import subprocess
import platform
import os
from datetime import datetime
from utils.keyboard import press_key, release_key

# Central MQTT server settings
CENTRAL_MQTT_SERVER = "31.44.2.222"
CENTRAL_MQTT_PORT = 1883
CENTRAL_MQTT_USERNAME = "kit"
CENTRAL_MQTT_PASSWORD = "1234"

# Local MQTT settings (will be dynamic)
LOCAL_MQTT_SERVER = "localhost"
LOCAL_MQTT_PORT = 1883

# Topics
DISCOVERY_TOPIC = "controller/discovery"
RESPONSE_TOPIC = "controller/response"
BASE_TOPIC = "gamecontroller"
REGISTER_TOPIC = f"{BASE_TOPIC}/register"
ID_TOPIC = f"{BASE_TOPIC}/getid"

# Controller tracking
controllers = {}
next_controller_id = 1
controller_lock = threading.Lock()

# Logging
log_callback = None


def set_log_callback(callback):
    """Set the callback function for logging"""
    global log_callback
    log_callback = callback


def log_event(message):
    """Log an event with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    if log_callback:
        log_callback(log_message)


def get_local_ip():
    """Get the local IP address"""
    try:
        # Connect to a remote server to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        log_event(f"Error getting local IP: {e}")
        return "127.0.0.1"


def is_mosquitto_running():
    """Check if local Mosquitto is running"""
    try:
        # Try to connect to the MQTT port to verify if something is actually listening
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(("localhost", LOCAL_MQTT_PORT))
        s.close()

        if result != 0:
            return False

        # Additional process check for Windows
        if platform.system() == "Windows":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq mosquitto.exe"],
                capture_output=True,
                text=True,
            )
            return "mosquitto.exe" in result.stdout
        else:
            # For non-Windows systems
            result = subprocess.run(["pgrep", "mosquitto"], capture_output=True)
            return result.returncode == 0
    except Exception as e:
        log_event(f"Error checking Mosquitto status: {e}")
        return False


def start_local_mosquitto():
    """Start local Mosquitto broker"""
    try:
        # Get the Client directory path (two levels up from this file)
        client_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(client_dir, "mosquitto.conf")

        # Verify the config file exists
        if not os.path.exists(config_path):
            log_event(f"Error: mosquitto.conf not found at {config_path}")
            return False

        if platform.system() == "Windows":
            # Try to start mosquitto with config
            subprocess.Popen(
                ["mosquitto", "-v", "-c", config_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            subprocess.Popen(["mosquitto", "-v", "-c", config_path])

        # Wait a moment for it to start
        import time

        time.sleep(2)
        return is_mosquitto_running()
    except Exception as e:
        log_event(f"Error starting Mosquitto: {e}")
        return False


# Central server client callbacks
def on_central_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the central MQTT broker"""
    if rc == 0:
        log_event("Connected to central MQTT server")
        client.subscribe(DISCOVERY_TOPIC)
    else:
        log_event(f"Failed to connect to central server with result code {rc}")


def on_central_message(client, userdata, msg):
    """Callback for when a message is received from the central MQTT broker"""
    topic = msg.topic
    payload = msg.payload.decode()

    log_event(f"Central server message: {topic} = {payload}")

    # Handle device discovery requests
    if topic == DISCOVERY_TOPIC:
        try:
            request = json.loads(payload)
            if request.get("action") == "discover_client":
                device_id = request.get("device_id", "unknown")

                # Ensure local Mosquitto is running
                if not is_mosquitto_running():
                    if start_local_mosquitto():
                        log_event("Started local Mosquitto broker")
                    else:
                        log_event("Failed to start local Mosquitto broker")
                        return

                # Respond with local IP and port
                response = {
                    "action": "client_info",
                    "device_id": device_id,
                    "ip": get_local_ip(),
                    "port": LOCAL_MQTT_PORT,
                    "client_id": "game_controller_client",
                }

                client.publish(RESPONSE_TOPIC, json.dumps(response))
                log_event(
                    f"Sent connection info to device {device_id}: {get_local_ip()}:{LOCAL_MQTT_PORT}"
                )

        except Exception as e:
            log_event(f"Error processing discovery message: {e}")


# Local server client callbacks
def on_local_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the local MQTT broker"""
    if rc == 0:
        # Get port from GUI if available
        port = LOCAL_MQTT_PORT
        if userdata and hasattr(userdata, "mosquitto_port_entry"):
            port_str = userdata.mosquitto_port_entry.get()
            if port_str and port_str.isdigit():
                port = int(port_str)

        # Verify Mosquitto is still running on the correct port
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(("localhost", port))
            s.close()

            if result != 0:
                log_event(
                    "Warning: Connected but Mosquitto server appears to be stopped"
                )
                client.disconnect()
                if userdata and hasattr(userdata, "update_mqtt_status"):
                    userdata.update_mqtt_status(False)
                return
        except:
            pass  # Continue even if port check fails

        log_event("Connected to local MQTT server")
        client.subscribe(REGISTER_TOPIC)
        client.subscribe(f"{BASE_TOPIC}/+/button")
        client.subscribe(f"{BASE_TOPIC}/+/joystick")

        # Update GUI connection status if available
        if userdata and hasattr(userdata, "update_mqtt_status"):
            userdata.update_mqtt_status(True)
    else:
        log_event(f"Failed to connect to local server with result code {rc}")
        # Update GUI connection status if available
        if userdata and hasattr(userdata, "update_mqtt_status"):
            userdata.update_mqtt_status(False)


def on_local_disconnect(client, userdata, rc):
    """Callback for when the client disconnects from the local MQTT broker"""
    if rc != 0:
        log_event(f"Unexpected disconnection from local MQTT server (rc={rc})")
    else:
        log_event("Disconnected from local MQTT server")

    # Update GUI connection status if available
    if userdata and hasattr(userdata, "update_mqtt_status"):
        userdata.update_mqtt_status(False)

    # Try to reconnect if Mosquitto is still running
    if is_mosquitto_running():
        log_event("Attempting to reconnect...")
        client.loop_stop()
        connect_to_local_mqtt(client)


def on_local_message(client, userdata, msg):
    """Callback for when a message is received from the local MQTT broker"""
    topic = msg.topic
    payload = msg.payload.decode()

    # New controller registration
    if topic == REGISTER_TOPIC and payload == "new":
        with controller_lock:
            global next_controller_id
            controller_id = str(next_controller_id)
            next_controller_id += 1

            # Create new controller
            from controller import GameController

            # Get settings manager from userdata if available
            settings_manager = None
            if userdata and hasattr(userdata, "settings_manager"):
                settings_manager = userdata.settings_manager
            controller = GameController(controller_id, settings_manager)
            controllers[controller_id] = controller

            # Send ID to the controller
            client.publish(ID_TOPIC, controller_id)

            log_event(f"New controller registered with ID: {controller_id}")

            # Notify the GUI of the new controller
            if userdata and hasattr(userdata, "update_controllers"):
                userdata.update_controllers(controllers)

    # Handle button press/release messages
    elif "/button" in topic:
        try:
            parts = topic.split("/")
            controller_id = parts[1]

            if controller_id in controllers:
                button_data = json.loads(payload)
                button_num = button_data.get("button")
                pressed = button_data.get("pressed", False)

                # Update controller state
                controllers[controller_id].button_states[button_num] = pressed

                # Map to key press/release
                button_key = f"button{button_num}"
                mapped_key = controllers[controller_id].key_mappings.get(button_key)

                if mapped_key:
                    action = "pressed" if pressed else "released"
                    log_event(
                        f"Controller {controller_id} {action} button {button_num} -> key '{mapped_key}'"
                    )

                    if pressed:
                        press_key(mapped_key)
                        controllers[controller_id].active_keys.add(mapped_key)
                    else:
                        release_key(mapped_key)
                        controllers[controller_id].active_keys.discard(mapped_key)

                # Update GUI if needed
                if userdata and hasattr(userdata, "update_controller_state"):
                    userdata.update_controller_state(
                        controller_id, "button", button_num, pressed
                    )
        except Exception as e:
            log_event(f"Error processing button message: {e}")

    # Handle joystick movement messages
    elif "/joystick" in topic:
        try:
            parts = topic.split("/")
            controller_id = parts[1]

            if controller_id in controllers:
                joystick_data = json.loads(payload)
                joystick_num = joystick_data.get("joystick")
                x = joystick_data.get("x", 512)
                y = joystick_data.get("y", 512)
                pressed = joystick_data.get("pressed", False)

                # Get previous joystick state
                prev_state = controllers[controller_id].joystick_states.get(
                    joystick_num, {"x": 512, "y": 512, "pressed": False}
                )
                prev_x = prev_state["x"]
                prev_y = prev_state["y"]

                # Update controller state
                controllers[controller_id].joystick_states[joystick_num] = {
                    "x": x,
                    "y": y,
                    "pressed": pressed,
                }

                # Handle joystick pressed state if needed
                if pressed != prev_state["pressed"] and pressed:
                    # Joystick button press logic can go here if needed
                    pass

                # Map joystick positions to key presses
                joystick_prefix = f"joystick{joystick_num}"

                # X-axis
                right_key = controllers[controller_id].key_mappings.get(
                    f"{joystick_prefix}_right"
                )
                left_key = controllers[controller_id].key_mappings.get(
                    f"{joystick_prefix}_left"
                )

                # Right
                if x > 800 and prev_x <= 800 and right_key:
                    press_key(right_key)
                    controllers[controller_id].active_keys.add(right_key)
                    log_event(
                        f"Controller {controller_id} joystick {joystick_num} moved right -> key '{right_key}'"
                    )
                elif x <= 800 and prev_x > 800 and right_key:
                    release_key(right_key)
                    controllers[controller_id].active_keys.discard(right_key)

                # Left
                if x < 200 and prev_x >= 200 and left_key:
                    press_key(left_key)
                    controllers[controller_id].active_keys.add(left_key)
                    log_event(
                        f"Controller {controller_id} joystick {joystick_num} moved left -> key '{left_key}'"
                    )
                elif x >= 200 and prev_x < 200 and left_key:
                    release_key(left_key)
                    controllers[controller_id].active_keys.discard(left_key)

                # Y-axis
                down_key = controllers[controller_id].key_mappings.get(
                    f"{joystick_prefix}_down"
                )
                up_key = controllers[controller_id].key_mappings.get(
                    f"{joystick_prefix}_up"
                )

                # Down
                if y > 800 and prev_y <= 800 and down_key:
                    press_key(down_key)
                    controllers[controller_id].active_keys.add(down_key)
                    log_event(
                        f"Controller {controller_id} joystick {joystick_num} moved down -> key '{down_key}'"
                    )
                elif y <= 800 and prev_y > 800 and down_key:
                    release_key(down_key)
                    controllers[controller_id].active_keys.discard(down_key)

                # Up
                if y < 200 and prev_y >= 200 and up_key:
                    press_key(up_key)
                    controllers[controller_id].active_keys.add(up_key)
                    log_event(
                        f"Controller {controller_id} joystick {joystick_num} moved up -> key '{up_key}'"
                    )
                elif y >= 200 and prev_y < 200 and up_key:
                    release_key(up_key)
                    controllers[controller_id].active_keys.discard(up_key)

                # Update GUI if needed
                if userdata and hasattr(userdata, "update_controller_state"):
                    userdata.update_controller_state(
                        controller_id, "joystick", joystick_num, (x, y)
                    )
        except Exception as e:
            log_event(f"Error processing joystick message: {e}")


def create_central_mqtt_client():
    """Create and configure a central MQTT client"""
    client = mqtt.Client()
    client.username_pw_set(CENTRAL_MQTT_USERNAME, CENTRAL_MQTT_PASSWORD)
    client.on_connect = on_central_connect
    client.on_message = on_central_message
    return client


def create_local_mqtt_client(userdata=None):
    """Create and configure a local MQTT client"""
    client = mqtt.Client(userdata=userdata)
    client.on_connect = on_local_connect
    client.on_message = on_local_message
    client.on_disconnect = on_local_disconnect

    # Enable automatic reconnection
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    return client


def connect_to_central_mqtt(client):
    """Connect to the central MQTT broker"""
    try:
        client.connect(CENTRAL_MQTT_SERVER, CENTRAL_MQTT_PORT, 60)
        client.loop_start()
        return True
    except Exception as e:
        log_event(f"Failed to connect to central MQTT server: {e}")
        return False


def connect_to_local_mqtt(client):
    """Connect to the local MQTT broker"""
    try:
        # First verify Mosquitto is actually running
        if not is_mosquitto_running():
            log_event("Cannot connect: Local Mosquitto server is not running")
            if (
                hasattr(client, "userdata")
                and client.userdata
                and hasattr(client.userdata, "update_mqtt_status")
            ):
                client.userdata.update_mqtt_status(False)
            return False

        # Get port from GUI if available
        port = LOCAL_MQTT_PORT
        if (
            hasattr(client, "userdata")
            and client.userdata
            and hasattr(client.userdata, "mosquitto_port_entry")
        ):
            port_str = client.userdata.mosquitto_port_entry.get()
            if port_str and port_str.isdigit():
                port = int(port_str)

        # Try to connect
        client.connect(LOCAL_MQTT_SERVER, port, keepalive=60)
        client.loop_start()
        return True
    except Exception as e:
        log_event(f"Failed to connect to local MQTT server: {e}")
        if (
            hasattr(client, "userdata")
            and client.userdata
            and hasattr(client.userdata, "update_mqtt_status")
        ):
            client.userdata.update_mqtt_status(False)
        return False


def cleanup_mqtt(client):
    """Clean up the MQTT client"""
    try:
        client.loop_stop()
        client.disconnect()
    except:
        pass


def cleanup_controllers():
    """Release any pressed keys for all controllers"""
    from utils.keyboard import release_key

    for controller in controllers.values():
        for key in controller.active_keys:
            release_key(key)
