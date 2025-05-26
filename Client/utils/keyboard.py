import sys

# Determine which keypress module to use based on the OS
if sys.platform == "darwin":  # macOS
    from .keyboard_mac import press_key, release_key, key_press
elif sys.platform == "win32":  # Windows
    from .keyboard_win import press_key, release_key, key_press
else:
    print(f"Unsupported platform: {sys.platform}")
    sys.exit(1)

# Export the functions
__all__ = ["press_key", "release_key", "key_press"]
