import os
import sys
import json
import socket
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import shutil


def setup_settings_tab(app):
    """Set up the settings tab with Mosquitto server management settings"""
    # Add methods to the app first
    add_methods_to_app(app)
    # Server Frame
    app.server_frame = ttk.LabelFrame(
        app.settings_frame, text="MQTT Server (Mosquitto)"
    )
    app.server_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Port
    ttk.Label(app.server_frame, text="Port:").grid(
        row=1, column=0, sticky=tk.W, padx=5, pady=5
    )

    # Create a StringVar with validation
    app.port_var = tk.StringVar(value="1883")
    app.port_var.trace_add(
        "write", lambda name, index, mode: app.validate_port(app.port_var.get())
    )

    app.mosquitto_port_entry = ttk.Entry(
        app.server_frame, textvariable=app.port_var, width=10
    )
    app.mosquitto_port_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

    # IP Address Display
    ttk.Label(app.server_frame, text="Server IP:").grid(
        row=2, column=0, sticky=tk.W, padx=5, pady=5
    )
    app.ip_display = ttk.Label(app.server_frame, text="Detecting...")
    app.ip_display.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

    # Status Frame with indicators
    app.status_frame = ttk.Frame(app.server_frame)
    app.status_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

    # Server status with indicator
    app.server_status_frame = ttk.Frame(app.status_frame)
    app.server_status_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))

    app.status_canvas = tk.Canvas(
        app.server_status_frame, width=20, height=20, highlightthickness=0
    )
    app.status_canvas.pack(side=tk.LEFT, padx=(0, 5))
    app.status_circle = app.status_canvas.create_oval(
        5, 5, 15, 15, fill="red", outline="darkred"
    )

    app.server_status_label = ttk.Label(
        app.server_status_frame, text="Server Status: Stopped"
    )
    app.server_status_label.pack(side=tk.LEFT)

    # MQTT status with indicator
    app.mqtt_status_frame = ttk.Frame(app.status_frame)
    app.mqtt_status_frame.pack(side=tk.TOP, fill=tk.X)

    app.mqtt_status_canvas = tk.Canvas(
        app.mqtt_status_frame, width=20, height=20, highlightthickness=0
    )
    app.mqtt_status_canvas.pack(side=tk.LEFT, padx=(0, 5))
    app.mqtt_status_circle = app.mqtt_status_canvas.create_oval(
        5, 5, 15, 15, fill="gray", outline="darkgray"
    )

    app.mqtt_status_label = ttk.Label(app.mqtt_status_frame, text="MQTT: Not Connected")
    app.mqtt_status_label.pack(side=tk.LEFT)

    # Start/Stop Button
    app.run_button = ttk.Button(
        app.server_frame, text="Start Mosquitto", command=app.toggle_mosquitto_server
    )
    app.run_button.grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

    # Set server_running flag
    app.server_running = False
    app.mosquitto_process = None

    # Get local IP and load saved settings
    app.get_local_ip()
    app.load_mosquitto_settings()

    # Check if server is already running
    if app.is_mqtt_server_running():
        app.server_running = True
        app.update_server_status(True)


def add_methods_to_app(app):
    """Add the methods required for the settings tab to the app"""

    # Add methods to the app - we need to create bound methods
    app.validate_port = lambda value: validate_port(app, value)
    app.apply_settings = lambda: apply_settings(app)
    app.get_local_ip = lambda: get_local_ip(app)
    app.load_mosquitto_settings = lambda: load_mosquitto_settings(app)
    app.save_mosquitto_settings = lambda: save_mosquitto_settings(app)
    app.is_mqtt_server_running = lambda: is_mqtt_server_running(app)
    app.toggle_mosquitto_server = lambda: toggle_mosquitto_server(app)
    app.connect_mqtt = lambda: connect_mqtt(app)
    app.set_connection_status = lambda connected: set_connection_status(app, connected)
    app.update_server_status = lambda status: update_server_status(app, status)
    app.update_mqtt_status = lambda status: update_mqtt_status(app, status)


def validate_port(app, value):
    """Validate port number - only allow digits and ensure it's in valid range"""
    # Remove any non-digit characters
    digits_only = "".join(c for c in value if c.isdigit())

    # Ensure it's within range 1-65535
    if digits_only:
        port_num = int(digits_only)
        if port_num < 1:
            digits_only = "1"
        elif port_num > 65535:
            digits_only = "65535"

    # If the filtered value is different from the input, update the entry
    if digits_only != value:
        app.port_var.set(digits_only)

    return True


def apply_settings(app):
    """Apply the MQTT settings - Kept for compatibility"""
    pass


def get_local_ip(app):
    """Get the local IP address of this machine"""
    try:
        # Create a socket to determine the IP address that would be used to connect externally
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            # This doesn't need to be reachable, just something external
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            # Fallback method
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
        finally:
            s.close()

        # Display the IP in the GUI
        if hasattr(app, "ip_display"):
            app.ip_display.config(text=ip)

        return ip
    except Exception as e:
        if hasattr(app, "ip_display"):
            app.ip_display.config(text=f"Error: {str(e)}")
        return "127.0.0.1"  # Fallback to localhost


def load_mosquitto_settings(app):
    """Load saved Mosquitto settings from file"""
    settings_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "mosquitto_settings.json"
    )

    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r") as f:
                settings = json.load(f)

                # Load saved port
                if "port" in settings and hasattr(app, "port_var"):
                    app.port_var.set(settings["port"])
        except Exception:
            # If there's an error, use defaults
            if hasattr(app, "port_var"):
                app.port_var.set("1883")
    else:
        # If no settings file, use defaults
        if hasattr(app, "port_var"):
            app.port_var.set("1883")


def save_mosquitto_settings(app):
    """Save Mosquitto settings to file"""
    # Create settings directory if it doesn't exist
    settings_dir = os.path.dirname(os.path.dirname(__file__))
    settings_file = os.path.join(settings_dir, "mosquitto_settings.json")

    settings = {}

    # Save port
    if hasattr(app, "port_var"):
        settings["port"] = app.port_var.get()

    # Save to file
    try:
        with open(settings_file, "w") as f:
            json.dump(settings, f)
    except Exception as e:
        print(f"Error saving settings: {e}")


def browse_for_mosquitto(app):
    """Open a file dialog to browse for the Mosquitto executable"""
    file_types = (
        [("Executable files", "*.exe")]
        if sys.platform == "win32"
        else [("All files", "*")]
    )

    file_path = filedialog.askopenfilename(
        title="Select Mosquitto Executable",
        filetypes=file_types,
        initialdir=(
            os.path.dirname(app.mosquitto_path_entry.get())
            if app.mosquitto_path_entry.get()
            else None
        ),
    )

    if file_path:
        app.mosquitto_path_entry.delete(0, tk.END)
        app.mosquitto_path_entry.insert(0, file_path)
        app.save_mosquitto_settings()  # Save the selection


def is_mqtt_server_running(app):
    """Check if MQTT server (Mosquitto) is already running"""
    try:
        # Get port from the UI or use default
        port = app.port_var.get().strip() if hasattr(app, "port_var") else "1883"
        if not port:
            port = "1883"

        # Create a socket and try to connect to the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # Short timeout for quick check
        result = sock.connect_ex(("localhost", int(port)))
        sock.close()

        # If port is open, something is listening there
        return result == 0
    except Exception:
        return False


def toggle_mosquitto_server(app):
    """Start or stop the Mosquitto server"""
    if app.server_running:
        # Stop the server
        try:
            if app.mosquitto_process:
                # Try to terminate the process
                if sys.platform == "win32":
                    subprocess.run(
                        [
                            "taskkill",
                            "/F",
                            "/T",
                            "/PID",
                            str(app.mosquitto_process.pid),
                        ],
                        capture_output=True,
                        check=False,
                    )
                else:
                    app.mosquitto_process.terminate()
                    app.mosquitto_process.wait(timeout=5)

                app.mosquitto_process = None

            # Update UI
            app.server_running = False
            app.run_button.config(text="Start Mosquitto")
            app.update_server_status(False)
            app.mosquitto_port_entry.config(state="normal")

            # Update MQTT connection status
            app.set_connection_status(False)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop Mosquitto: {e}")
    else:
        # Start the server
        try:
            # Get port from entry
            port = app.port_var.get().strip()
            if not port:
                port = "1883"  # Default port
                app.port_var.set(port)

            # Check if already running
            if app.is_mqtt_server_running():
                app.server_running = True
                app.run_button.config(text="Stop Mosquitto")
                app.update_server_status(True)

                # Connect to the already running server
                if hasattr(app, "mqtt_client") and app.mqtt_client:
                    app.connect_mqtt()

                return

            # Save current port setting
            app.save_mosquitto_settings()

            # Start Mosquitto with the specified port and verbose flag
            try:
                app.mosquitto_process = subprocess.Popen(
                    ["mosquitto", "-v", "-p", port],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=False,  # Don't use shell to avoid path issues
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    ),
                )

                # Update UI
                app.server_running = True
                app.run_button.config(text="Stop Mosquitto")
                app.update_server_status(True)
                app.mosquitto_port_entry.config(state="readonly")

                # Connect to MQTT server now that Mosquitto is running
                if hasattr(app, "mqtt_client") and app.mqtt_client:
                    # Wait a brief moment for Mosquitto to initialize
                    app.after(1000, app.connect_mqtt)

            except FileNotFoundError:
                messagebox.showerror(
                    "Error",
                    "Mosquitto executable not found. Make sure 'mosquitto' is in your system PATH.",
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start Mosquitto: {e}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start Mosquitto: {e}")


def connect_mqtt(app):
    """Connect to the MQTT server after Mosquitto has been started"""
    if not hasattr(app, "mqtt_client") or not app.mqtt_client:
        return

    try:
        # Get port from UI or use default
        port = int(app.port_var.get()) if app.port_var.get() else 1883

        # Connect to MQTT server
        app.mqtt_client.connect("localhost", port, 60)
        app.mqtt_client.loop_start()
        app.set_connection_status(True)
        print(f"Connected to MQTT server on port {port}")
    except Exception as e:
        print(f"Failed to connect to MQTT server: {e}")
        app.set_connection_status(False)


def set_connection_status(app, connected):
    """Update the MQTT connection status display"""
    if connected:
        app.mqtt_status_canvas.itemconfig(
            app.mqtt_status_circle, fill="green", outline="darkgreen"
        )
        app.mqtt_status_label.config(text="MQTT: Connected")
    else:
        app.mqtt_status_canvas.itemconfig(
            app.mqtt_status_circle, fill="gray", outline="darkgray"
        )
        app.mqtt_status_label.config(text="MQTT: Not Connected")


def update_server_status(app, status):
    """Update the server status display"""
    if status:
        app.status_canvas.itemconfig(
            app.status_circle, fill="green", outline="darkgreen"
        )
        app.server_status_label.config(text="Server Status: Running")
    else:
        app.status_canvas.itemconfig(app.status_circle, fill="red", outline="darkred")
        app.server_status_label.config(text="Server Status: Stopped")


def update_mqtt_status(app, status):
    """Update the MQTT connection status display"""
    if status:
        app.mqtt_status_label.config(text="MQTT Connected", foreground="green")
    else:
        app.mqtt_status_label.config(text="MQTT Not Connected", foreground="gray")
