from Quartz.CoreGraphics import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    kCGHIDEventTap,
    kCGEventKeyDown,
    kCGEventKeyUp,
)
import time

# Key code mappings for macOS
KEY_CODES = {
    "a": 0x00,
    "b": 0x0B,
    "c": 0x08,
    "d": 0x02,
    "e": 0x0E,
    "f": 0x03,
    "g": 0x05,
    "h": 0x04,
    "i": 0x22,
    "j": 0x26,
    "k": 0x28,
    "l": 0x25,
    "m": 0x2E,
    "n": 0x2D,
    "o": 0x1F,
    "p": 0x23,
    "q": 0x0C,
    "r": 0x0F,
    "s": 0x01,
    "t": 0x11,
    "u": 0x20,
    "v": 0x09,
    "w": 0x0D,
    "x": 0x07,
    "y": 0x10,
    "z": 0x06,
    "0": 0x1D,
    "1": 0x12,
    "2": 0x13,
    "3": 0x14,
    "4": 0x15,
    "5": 0x17,
    "6": 0x16,
    "7": 0x1A,
    "8": 0x1C,
    "9": 0x19,
    "space": 0x31,
    "enter": 0x24,
    "tab": 0x30,
    "escape": 0x35,
    "backspace": 0x33,
    "up": 0x7E,
    "down": 0x7D,
    "left": 0x7B,
    "right": 0x7C,
    "ctrl": 0x3B,
    "alt": 0x3A,
    "shift": 0x38,
    "caps_lock": 0x39,
    "f1": 0x7A,
    "f2": 0x78,
    "f3": 0x63,
    "f4": 0x76,
    "f5": 0x60,
    "f6": 0x61,
    "f7": 0x62,
    "f8": 0x64,
    "f9": 0x65,
    "f10": 0x6D,
    "f11": 0x67,
    "f12": 0x6F,
}


def press_key(key):
    """Press a key down"""
    if key.lower() in KEY_CODES:
        key_code = KEY_CODES[key.lower()]
        event = CGEventCreateKeyboardEvent(None, key_code, True)
        CGEventPost(kCGHIDEventTap, event)
    else:
        print(f"Key '{key}' not supported")


def release_key(key):
    """Release a key"""
    if key.lower() in KEY_CODES:
        key_code = KEY_CODES[key.lower()]
        event = CGEventCreateKeyboardEvent(None, key_code, False)
        CGEventPost(kCGHIDEventTap, event)
    else:
        print(f"Key '{key}' not supported")


def key_press(key, duration=0.1):
    """Press and release a key with a given duration"""
    press_key(key)
    time.sleep(duration)
    release_key(key)
