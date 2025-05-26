"""
Test Script for Restructured Application
---------------------------------------
This script tests the imports and basic functionality of the restructured application.
"""
import os
import sys

# Test imports from all packages
print("Testing imports...")

# Test controller package
try:
    from controller import GameController, DEFAULT_MAPPINGS
    print("[PASS] Controller package imported successfully")
except ImportError as e:
    print(f"[FAIL] Controller package import failed: {e}")

# Test utils package
try:
    from utils import press_key, release_key, key_press
    print("[PASS] Utils package imported successfully")
except ImportError as e:
    print(f"[FAIL] Utils package import failed: {e}")

# Test mqtt package
try:
    from mqtt import (
        create_mqtt_client,
        connect_to_mqtt,
        cleanup_mqtt,
        cleanup_controllers,
        controllers,
        MQTT_SERVER,
        MQTT_PORT,
        BASE_TOPIC
    )
    print("[PASS] MQTT package imported successfully")
except ImportError as e:
    print(f"[FAIL] MQTT package import failed: {e}")

# Test gui package
try:
    from gui import GameControllerGUI
    print("[PASS] GUI package imported successfully")
except ImportError as e:
    print(f"[FAIL] GUI package import failed: {e}")

# Test creating a controller
try:
    controller = GameController("test")
    print(f"[PASS] Created controller with ID: {controller.id}")
except Exception as e:
    print(f"[FAIL] Controller creation failed: {e}")

# Test modifying and saving controller mappings
try:
    controller.update_key_mapping("button1", "z")
    print(f"[PASS] Updated controller mapping: button1 -> {controller.key_mappings['button1']}")
    
    controller.save_mappings()
    print(f"[PASS] Saved controller mappings")
except Exception as e:
    print(f"[FAIL] Controller mapping operations failed: {e}")

print("\nAll tests completed. If all tests passed, the restructured application should work correctly.")
print("You can now run 'python main_final.py' to start the application with the new structure.")
