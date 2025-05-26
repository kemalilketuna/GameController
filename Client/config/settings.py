import json
import os
from typing import Dict, Any


class SettingsManager:
    """Manages application settings and key mappings"""

    def __init__(self, config_dir="config"):
        self.config_dir = config_dir
        self.default_mappings_file = os.path.join(config_dir, "default_mappings.json")
        self.mosquitto_settings_file = os.path.join(
            config_dir, "mosquitto_settings.json"
        )

        # Ensure config directory exists
        os.makedirs(config_dir, exist_ok=True)

        # Default key mappings
        self.default_mappings = {
            "button1": "space",
            "button2": "x",
            "button3": "z",
            "button4": "c",
            "button5": "l",  # L3 button
            "button6": "r",  # R3 button
            "joystick1_up": "w",
            "joystick1_down": "s",
            "joystick1_left": "a",
            "joystick1_right": "d",
            "joystick2_up": "up",
            "joystick2_down": "down",
            "joystick2_left": "left",
            "joystick2_right": "right",
        }

    def load_default_mappings(self) -> Dict[str, str]:
        """Load default key mappings from file, create if doesn't exist"""
        try:
            if os.path.exists(self.default_mappings_file):
                with open(self.default_mappings_file, "r") as f:
                    data = json.load(f)
                    return data.get("key_mappings", self.default_mappings)
            else:
                # Create default file
                self.save_default_mappings(self.default_mappings)
                return self.default_mappings
        except Exception as e:
            print(f"Error loading default mappings: {e}")
            return self.default_mappings

    def save_default_mappings(self, mappings: Dict[str, str]):
        """Save default key mappings to file"""
        try:
            data = {"name": "Default Controller Mapping", "key_mappings": mappings}
            with open(self.default_mappings_file, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Saved default mappings to {self.default_mappings_file}")
        except Exception as e:
            print(f"Error saving default mappings: {e}")

    def load_controller_mappings(self, controller_id: str) -> Dict[str, str]:
        """Load key mappings for a specific controller"""
        controller_file = os.path.join(
            self.config_dir, f"controller_{controller_id}.json"
        )
        try:
            if os.path.exists(controller_file):
                with open(controller_file, "r") as f:
                    data = json.load(f)
                    return data.get("key_mappings", self.load_default_mappings())
            else:
                # Return default mappings for new controllers
                return self.load_default_mappings()
        except Exception as e:
            print(f"Error loading controller {controller_id} mappings: {e}")
            return self.load_default_mappings()

    def save_controller_mappings(
        self, controller_id: str, mappings: Dict[str, str], name: str = None
    ):
        """Save key mappings for a specific controller"""
        controller_file = os.path.join(
            self.config_dir, f"controller_{controller_id}.json"
        )
        try:
            data = {
                "id": controller_id,
                "name": name or f"Controller {controller_id}",
                "key_mappings": mappings,
            }
            with open(controller_file, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Saved controller {controller_id} mappings to {controller_file}")
        except Exception as e:
            print(f"Error saving controller {controller_id} mappings: {e}")

    def load_mosquitto_settings(self) -> Dict[str, Any]:
        """Load Mosquitto settings"""
        try:
            if os.path.exists(self.mosquitto_settings_file):
                with open(self.mosquitto_settings_file, "r") as f:
                    return json.load(f)
            else:
                # Return default settings
                default_settings = {
                    "path": (
                        "mosquitto"
                        if os.name != "nt"
                        else "C:/Program Files/mosquitto/mosquitto.exe"
                    ),
                    "port": "1883",
                }
                self.save_mosquitto_settings(default_settings)
                return default_settings
        except Exception as e:
            print(f"Error loading Mosquitto settings: {e}")
            return {"path": "mosquitto", "port": "1883"}

    def save_mosquitto_settings(self, settings: Dict[str, Any]):
        """Save Mosquitto settings"""
        try:
            with open(self.mosquitto_settings_file, "w") as f:
                json.dump(settings, f, indent=2)
            print(f"Saved Mosquitto settings to {self.mosquitto_settings_file}")
        except Exception as e:
            print(f"Error saving Mosquitto settings: {e}")

    def get_all_controller_files(self) -> list:
        """Get list of all controller configuration files"""
        try:
            files = []
            for filename in os.listdir(self.config_dir):
                if filename.startswith("controller_") and filename.endswith(".json"):
                    files.append(filename)
            return sorted(files)
        except Exception as e:
            print(f"Error getting controller files: {e}")
            return []
