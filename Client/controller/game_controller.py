import os
import json
from config.settings import SettingsManager

# Default key mappings
DEFAULT_MAPPINGS = {
    "button1": "space",
    "button2": "x",
    "button3": "z",
    "button4": "c",
    "joystick1_up": "w",
    "joystick1_down": "s",
    "joystick1_left": "a",
    "joystick1_right": "d",
    "joystick2_up": "up",
    "joystick2_down": "down",
    "joystick2_left": "left",
    "joystick2_right": "right",
}


class GameController:
    def __init__(self, controller_id, settings_manager=None):
        self.id = controller_id
        self.name = f"Controller {controller_id}"
        self.button_states = {
            1: False,
            2: False,
            3: False,
            4: False,
            5: False,
            6: False,
        }
        self.joystick_states = {
            1: {"x": 512, "y": 512, "pressed": False},
            2: {"x": 512, "y": 512, "pressed": False},
        }
        self.active_keys = set()

        # Use settings manager for key mappings
        self.settings_manager = settings_manager or SettingsManager()
        self.key_mappings = self.settings_manager.load_controller_mappings(
            controller_id
        )

    def update_key_mapping(self, control, key):
        """Update a key mapping for this controller"""
        self.key_mappings[control] = key

    def save_mappings(self):
        """Save the controller's key mappings to a file"""
        self.settings_manager.save_controller_mappings(
            self.id, self.key_mappings, self.name
        )

    def load_mappings(self):
        """Load the controller's key mappings from a file if it exists"""
        try:
            self.key_mappings = self.settings_manager.load_controller_mappings(self.id)
            return True
        except Exception as e:
            print(f"Error loading mappings for controller {self.id}: {e}")
            self.key_mappings = DEFAULT_MAPPINGS.copy()
            return False

    def reset_to_defaults(self):
        """Reset key mappings to default values"""
        self.key_mappings = self.settings_manager.load_default_mappings().copy()

    def get_mapping_info(self):
        """Get information about this controller's mappings"""
        return {
            "id": self.id,
            "name": self.name,
            "key_mappings": self.key_mappings.copy(),
            "button_states": self.button_states.copy(),
            "joystick_states": self.joystick_states.copy(),
        }
