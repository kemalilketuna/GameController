#!/usr/bin/env python3
"""
ESP32 Controller Simulation
This script simulates an ESP32 controller connecting to the system for testing.
"""

import paho.mqtt.client as mqtt
import json
import time
import random
import threading

# Central server settings
CENTRAL_SERVER = "31.44.2.222"
CENTRAL_PORT = 1883
CENTRAL_USERNAME = "kit"
CENTRAL_PASSWORD = "1234"

# Topics
DISCOVERY_TOPIC = "controller/discovery"
RESPONSE_TOPIC = "controller/response"
BASE_TOPIC = "gamecontroller"


class ESP32ControllerSimulation:
    def __init__(self):
        self.device_id = f"ESP32-SIM-{random.randint(1000, 9999)}"
        self.controller_id = None
        self.local_client_ip = None
        self.local_client_port = None

        # MQTT clients
        self.central_client = None
        self.local_client = None

        # State
        self.registered_to_central = False
        self.connected_to_local = False

        print(f"Starting ESP32 Controller Simulation with device ID: {self.device_id}")

    def on_central_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to central MQTT server")
            client.subscribe(RESPONSE_TOPIC)
            self.registered_to_central = True

            # Send discovery request
            request = {"action": "discover_client", "device_id": self.device_id}
            client.publish(DISCOVERY_TOPIC, json.dumps(request))
            print("Sent discovery request")
        else:
            print(f"Failed to connect to central server: {rc}")

    def on_central_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            print(f"Central server response: {payload}")

            if (
                payload.get("action") == "client_info"
                and payload.get("device_id") == self.device_id
            ):

                self.local_client_ip = payload.get("ip")
                self.local_client_port = payload.get("port", 1883)

                print(
                    f"Received client info: {self.local_client_ip}:{self.local_client_port}"
                )

                # Connect to local client
                self.connect_to_local()

        except Exception as e:
            print(f"Error processing central message: {e}")

    def on_local_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to local MQTT client")
            # Subscribe to controller ID topic
            client.subscribe(f"{BASE_TOPIC}/getid")

            # Request a controller ID
            client.publish(f"{BASE_TOPIC}/register", "new")
            print("Requested controller ID")
        else:
            print(f"Failed to connect to local client: {rc}")

    def on_local_message(self, client, userdata, msg):
        topic = msg.topic
        message = msg.payload.decode()

        print(f"Local message: {topic} = {message}")

        if topic == f"{BASE_TOPIC}/getid":
            self.controller_id = message
            self.connected_to_local = True
            print(f"Assigned controller ID: {self.controller_id}")

            # Start sending simulated input
            threading.Thread(target=self.simulate_input, daemon=True).start()

    def connect_to_central(self):
        """Connect to central MQTT server"""
        try:
            self.central_client = mqtt.Client()
            self.central_client.username_pw_set(CENTRAL_USERNAME, CENTRAL_PASSWORD)
            self.central_client.on_connect = self.on_central_connect
            self.central_client.on_message = self.on_central_message

            print(f"Connecting to central server: {CENTRAL_SERVER}:{CENTRAL_PORT}")
            self.central_client.connect(CENTRAL_SERVER, CENTRAL_PORT, 60)
            self.central_client.loop_start()

        except Exception as e:
            print(f"Failed to connect to central server: {e}")
            return False

        return True

    def connect_to_local(self):
        """Connect to local MQTT client"""
        if not self.local_client_ip:
            print("No local client info available")
            return

        try:
            self.local_client = mqtt.Client()
            self.local_client.on_connect = self.on_local_connect
            self.local_client.on_message = self.on_local_message

            print(
                f"Connecting to local client: {self.local_client_ip}:{self.local_client_port}"
            )
            self.local_client.connect(self.local_client_ip, self.local_client_port, 60)
            self.local_client.loop_start()

        except Exception as e:
            print(f"Failed to connect to local client: {e}")

    def send_button_input(self, button_num, pressed):
        """Send button input to local client"""
        if not self.connected_to_local or not self.controller_id:
            return

        message = {"button": button_num, "pressed": pressed}

        topic = f"{BASE_TOPIC}/{self.controller_id}/button"
        self.local_client.publish(topic, json.dumps(message))
        print(f"Sent button {button_num} {'pressed' if pressed else 'released'}")

    def send_joystick_input(self, joystick_num, x, y, pressed=False):
        """Send joystick input to local client"""
        if not self.connected_to_local or not self.controller_id:
            return

        message = {"joystick": joystick_num, "x": x, "y": y, "pressed": pressed}

        topic = f"{BASE_TOPIC}/{self.controller_id}/joystick"
        self.local_client.publish(topic, json.dumps(message))
        print(f"Sent joystick {joystick_num} position: ({x}, {y})")

    def simulate_input(self):
        """Simulate controller input in a loop"""
        print("Starting input simulation...")

        button_cycle = 0
        while self.connected_to_local:
            # Simulate button presses
            if button_cycle % 8 < 4:
                button_num = (button_cycle % 4) + 1
                self.send_button_input(button_num, True)
                time.sleep(0.5)
                self.send_button_input(button_num, False)

            # Simulate joystick movement
            if button_cycle % 6 == 0:
                # Move joystick 1 in a pattern
                positions = [
                    (512, 200),  # Up
                    (800, 512),  # Right
                    (512, 800),  # Down
                    (200, 512),  # Left
                    (512, 512),  # Center
                ]
                pos = positions[button_cycle % 5]
                self.send_joystick_input(1, pos[0], pos[1])

            button_cycle += 1
            time.sleep(2)

    def run(self):
        """Run the simulation"""
        # Connect to central server
        if not self.connect_to_central():
            return

        # Wait for connection and discovery
        timeout = 30
        start_time = time.time()

        while not self.connected_to_local and (time.time() - start_time) < timeout:
            time.sleep(1)

        if self.connected_to_local:
            print("Simulation connected successfully!")
            print("Press Ctrl+C to stop simulation")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping simulation...")
        else:
            print("Failed to connect within timeout")

        # Cleanup
        if self.central_client:
            self.central_client.loop_stop()
            self.central_client.disconnect()

        if self.local_client:
            self.local_client.loop_stop()
            self.local_client.disconnect()


if __name__ == "__main__":
    sim = ESP32ControllerSimulation()
    sim.run()
