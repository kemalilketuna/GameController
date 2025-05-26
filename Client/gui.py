import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import json
import socket
import subprocess
import shutil
import time

# Import DEFAULT_MAPPINGS from main module
try:
    from main import DEFAULT_MAPPINGS
except ImportError:
    # Fallback if import fails
    DEFAULT_MAPPINGS = {
        "button1": "a",
        "button2": "s",
        "button3": "d",
        "button4": "f",
        "joystick1_up": "",
        "joystick1_down": "",
        "joystick1_left": "",
        "joystick1_right": "",
        "joystick2_up": "",
        "joystick2_down": "",
        "joystick2_left": "",
        "joystick2_right": "",
    }


class GameControllerGUI(tk.Tk):
    def __init__(self, controllers, settings_manager=None):
        super().__init__()

        self.title("Game Controller Configuration")
        self.geometry("800x600")

        # Initialize variables
        self.controllers = controllers or {}
        self.settings_manager = settings_manager
        self.server_running = False
        self.mosquitto_process = None

        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.setup_tabs()

        # Check initial Mosquitto state
        if self.is_mqtt_server_running():
            self.server_running = True
            self.update_server_status(True)
            self.run_button.config(text="Stop Mosquitto")
            if hasattr(self, "mosquitto_port_entry"):
                self.mosquitto_port_entry.config(state="readonly")

        # Set up window close handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Set application icon
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "assets",
            "bat-black-silhouette-with-opened-wings.png",
        )
        if os.path.exists(icon_path):
            try:
                # Load and set the icon
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.iconphoto(True, icon_photo)
                # Keep a reference to prevent garbage collection
                self._icon_photo = icon_photo
            except Exception as e:
                print(f"Error loading application icon: {e}")

        self.central_mqtt_client = None
        self.local_mqtt_client = None

        # Variable to keep track of the currently selected controller
        self.selected_controller_id = None
        self.controller_frames = {}

        # Load the controller image
        image_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "assets", "sm_black_top.png"
        )
        if os.path.exists(image_path):
            try:
                self.controller_image = Image.open(image_path)
                self.controller_image = self.controller_image.resize(
                    (400, 300), Image.LANCZOS
                )
                self.controller_photo = ImageTk.PhotoImage(self.controller_image)
            except Exception as e:
                print(f"Error loading controller image: {e}")
                self.controller_photo = None
        else:
            print(f"Controller image not found at {image_path}")
            self.controller_photo = None

        # Create placeholder for controller map tab
        self.controller_map_frame = None
        self.mapping_buttons = {}
        self.listening_for_key = False
        self.current_mapping_control = None

        # Bind key press events for mapping
        self.bind("<Key>", self.on_key_press)

    def setup_tabs(self):
        """Set up the tabs for the GUI"""
        # Create the controllers tab
        self.controllers_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.controllers_frame, text="Controllers")
        self.setup_controllers_tab()

        # Create the settings tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        self.setup_settings_tab()

        # Create the log tab
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="Logs")
        self.setup_log_tab()

    def setup_controllers_tab(self):
        """Set up the controllers tab with a list of connected controllers"""
        # Create a frame for the controller list
        self.controllers_list_frame = ttk.LabelFrame(
            self.controllers_frame, text="Connected Controllers"
        )
        self.controllers_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create a listbox for the controllers
        self.controllers_listbox = tk.Listbox(self.controllers_list_frame, height=10)
        self.controllers_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.controllers_listbox.bind("<<ListboxSelect>>", self.on_controller_select)

        # Add a refresh button
        self.refresh_button = ttk.Button(
            self.controllers_list_frame,
            text="Refresh",
            command=self.refresh_controllers,
        )
        self.refresh_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Add a configure button
        self.configure_button = ttk.Button(
            self.controllers_list_frame,
            text="Configure",
            command=self.configure_selected_controller,
        )
        self.configure_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Status label
        self.status_label = ttk.Label(
            self.controllers_frame, text="Waiting for controllers..."
        )
        self.status_label.pack(pady=10)

    def setup_settings_tab(self):
        """Set up the settings tab with Mosquitto server management settings"""
        # Create a frame for Mosquitto server management
        self.server_frame = ttk.LabelFrame(
            self.settings_frame, text="Mosquitto Server Management"
        )
        self.server_frame.pack(fill=tk.X, padx=10, pady=10)

        # Local IP display (non-editable)
        ttk.Label(self.server_frame, text="Local IP:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.ip_display = ttk.Entry(self.server_frame, state="readonly")
        self.ip_display.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

        # Add refresh IP button
        self.refresh_ip_button = ttk.Button(
            self.server_frame, text="Refresh IP", command=self.refresh_ip_display
        )
        self.refresh_ip_button.grid(row=0, column=2, padx=5, pady=5)

        # Initial IP display
        self.refresh_ip_display()

        # Mosquitto port configuration
        ttk.Label(self.server_frame, text="Mosquitto Port:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.mosquitto_port_entry = ttk.Entry(self.server_frame)
        self.mosquitto_port_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)

        # Add validation for port entry (numbers only)
        self.port_validation = self.register(self.validate_port)
        self.mosquitto_port_entry.config(
            validate="key", validatecommand=(self.port_validation, "%P")
        )

        # Load saved port if available
        saved_port = self.load_mosquitto_settings().get("port", "1883")
        self.mosquitto_port_entry.insert(0, saved_port)

        # Run/Stop button
        self.run_button = ttk.Button(
            self.server_frame,
            text="Run Mosquitto",
            command=self.toggle_mosquitto_server,
        )
        self.run_button.grid(row=2, column=1, sticky=tk.E, padx=5, pady=5)

        # Status frame with indicators
        self.status_frame = ttk.Frame(self.server_frame)
        self.status_frame.grid(
            row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5
        )

        # Server status with indicator
        self.server_status_frame = ttk.Frame(self.status_frame)
        self.server_status_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))

        self.status_canvas = tk.Canvas(
            self.server_status_frame, width=20, height=20, highlightthickness=0
        )
        self.status_canvas.pack(side=tk.LEFT, padx=(0, 5))
        self.status_circle = self.status_canvas.create_oval(
            5, 5, 15, 15, fill="red", outline="darkred"
        )

        self.server_status_label = ttk.Label(
            self.server_status_frame, text="Server Status: Stopped"
        )
        self.server_status_label.pack(side=tk.LEFT)

        # MQTT status frame
        self.mqtt_status_frame = ttk.Frame(self.status_frame)
        self.mqtt_status_frame.pack(side=tk.TOP, fill=tk.X)

        # Local MQTT status
        self.mqtt_status_canvas = tk.Canvas(
            self.mqtt_status_frame, width=20, height=20, highlightthickness=0
        )
        self.mqtt_status_canvas.pack(side=tk.LEFT, padx=(0, 5))
        self.mqtt_status_circle = self.mqtt_status_canvas.create_oval(
            5, 5, 15, 15, fill="red", outline="darkred"
        )

        self.mqtt_status_label = ttk.Label(
            self.mqtt_status_frame, text="Local MQTT: Not Connected"
        )
        self.mqtt_status_label.pack(side=tk.LEFT)

        # Central MQTT status
        self.central_mqtt_canvas = tk.Canvas(
            self.mqtt_status_frame, width=20, height=20, highlightthickness=0
        )
        self.central_mqtt_canvas.pack(side=tk.LEFT, padx=(20, 5))
        self.central_mqtt_circle = self.central_mqtt_canvas.create_oval(
            5, 5, 15, 15, fill="red", outline="darkred"
        )

        self.central_mqtt_label = ttk.Label(
            self.mqtt_status_frame, text="Central MQTT: Not Connected"
        )
        self.central_mqtt_label.pack(side=tk.LEFT)

        # Configure column weights
        self.server_frame.columnconfigure(1, weight=1)

        # About information
        self.about_frame = ttk.LabelFrame(self.settings_frame, text="About")
        self.about_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(self.about_frame, text="Bat Controller Configuration").pack(
            padx=5, pady=5
        )
        ttk.Label(self.about_frame, text="Version 1.0").pack(padx=5, pady=5)
        ttk.Label(
            self.about_frame,
            text="A utility for configuring ESP32-based bat-shaped game controllers",
        ).pack(padx=5, pady=5)

    def setup_log_tab(self):
        """Set up the log tab with a text widget for displaying logs"""
        # Create text widget and scrollbar
        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(
            self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Add clear button
        self.clear_button = ttk.Button(
            self.log_frame, text="Clear Logs", command=self.clear_logs
        )
        self.clear_button.pack(pady=5)

        # Configure tag for timestamps
        self.log_text.tag_configure("timestamp", foreground="gray")

    def add_log_message(self, message):
        """Add a message to the log display"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)  # Auto-scroll to bottom

    def clear_logs(self):
        """Clear the log text widget"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def save_log(self):
        """Save the log to a file"""
        from tkinter import filedialog
        from datetime import datetime

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Log File",
            initialfile=f"controller_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )

        if filename:
            try:
                with open(filename, "w") as f:
                    log_content = self.log_text.get(1.0, tk.END)
                    f.write(log_content)
                messagebox.showinfo("Success", f"Log saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log: {e}")

    def set_central_connection_status(self, connected):
        """Update the central server connection status"""
        # This method is kept for compatibility but uses the new status indicators
        pass

    def set_local_connection_status(self, connected):
        """Update the local server connection status"""
        # Update using the new unified status indicators
        self.update_mqtt_status(connected)

    def update_controllers(self, controllers):
        """Update the list of controllers"""
        self.controllers = controllers
        self.refresh_controllers()

    def refresh_controllers(self):
        """Refresh the listbox of controllers"""
        self.controllers_listbox.delete(0, tk.END)

        # Add all current controllers to the listbox
        for controller_id, controller in self.controllers.items():
            display_name = f"Controller {controller_id}"
            if hasattr(controller, "name") and controller.name:
                display_name = f"{display_name} ({controller.name})"
            self.controllers_listbox.insert(tk.END, display_name)

        # Update status label
        if self.controllers:
            self.status_label.config(
                text=f"{len(self.controllers)} controller(s) connected"
            )
        else:
            self.status_label.config(text="Waiting for controllers...")

    def update_server_status(self, is_running):
        """Update the server status display"""
        if is_running:
            self.status_canvas.itemconfig(
                self.status_circle, fill="green", outline="darkgreen"
            )
            self.server_status_label.config(
                text="Server Status: Running", foreground="green"
            )
        else:
            self.status_canvas.itemconfig(
                self.status_circle, fill="red", outline="darkred"
            )
            self.server_status_label.config(
                text="Server Status: Stopped", foreground="red"
            )

    def update_mqtt_status(self, is_connected):
        """Update the MQTT connection status display"""
        if is_connected:
            self.mqtt_status_canvas.itemconfig(
                self.mqtt_status_circle, fill="green", outline="darkgreen"
            )
            self.mqtt_status_label.config(
                text="Local MQTT: Connected", foreground="green"
            )
        else:
            self.mqtt_status_canvas.itemconfig(
                self.mqtt_status_circle, fill="red", outline="darkred"
            )
            self.mqtt_status_label.config(
                text="Local MQTT: Not Connected", foreground="black"
            )

    def update_central_mqtt_status(self, is_connected):
        """Update the central MQTT connection status display"""
        if is_connected:
            self.central_mqtt_canvas.itemconfig(
                self.central_mqtt_circle, fill="green", outline="darkgreen"
            )
            self.central_mqtt_label.config(
                text="Central MQTT: Connected", foreground="green"
            )
        else:
            self.central_mqtt_canvas.itemconfig(
                self.central_mqtt_circle, fill="red", outline="darkred"
            )
            self.central_mqtt_label.config(
                text="Central MQTT: Not Connected", foreground="black"
            )

    def on_controller_select(self, event):
        """Handle selection of a controller from the listbox"""
        selection = self.controllers_listbox.curselection()
        if selection:
            index = selection[0]
            controller_id = list(self.controllers.keys())[index]
            self.selected_controller_id = controller_id

    def configure_selected_controller(self):
        """Open the configuration tab for the selected controller"""
        if not self.selected_controller_id:
            messagebox.showinfo("No Selection", "Please select a controller first")
            return

        # Check if a tab already exists for this controller
        tab_name = f"Controller {self.selected_controller_id}"

        # Remove existing tab if it exists
        for tab_id in range(self.notebook.index("end")):
            if self.notebook.tab(tab_id, "text") == tab_name:
                self.notebook.forget(tab_id)
                break

        # Create a new tab for this controller
        self.controller_map_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.controller_map_frame, text=tab_name)
        self.notebook.select(self.notebook.index("end") - 1)

        # Set up the controller mapping UI
        self.setup_controller_mapping(self.selected_controller_id)

    def setup_controller_mapping(self, controller_id):
        """Set up the UI for mapping controller buttons to keys"""
        controller = self.controllers[controller_id]

        # Controller name frame
        name_frame = ttk.Frame(self.controller_map_frame)
        name_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(name_frame, text="Controller Name:").pack(side=tk.LEFT, padx=5)
        name_entry = ttk.Entry(name_frame, width=30)
        name_entry.pack(side=tk.LEFT, padx=5)
        name_entry.insert(0, controller.name)

        def update_name():
            controller.name = name_entry.get()
            self.refresh_controllers()
            self.notebook.tab(
                self.notebook.select(), text=f"Controller {controller.name}"
            )

        ttk.Button(name_frame, text="Update Name", command=update_name).pack(
            side=tk.LEFT, padx=5
        )

        # Controller image and mapping buttons
        if self.controller_photo:
            # Container for image and buttons
            mapping_frame = ttk.Frame(self.controller_map_frame)
            mapping_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Canvas for image and overlaid buttons
            canvas = tk.Canvas(mapping_frame, width=400, height=300)
            canvas.pack(padx=10, pady=10)

            # Draw controller image
            canvas.create_image(200, 150, image=self.controller_photo)

            # Draw mapping buttons in a horizontal row
            # Use y=160 for all buttons to place them on the same axis

            # Button 3 (yellow) - far left
            self.add_mapping_button(canvas, controller_id, "button3", 60, 200)

            # Button 2 (blue) - middle left
            self.add_mapping_button(canvas, controller_id, "button2", 150, 200)

            # Button 1 (red) - middle right
            self.add_mapping_button(canvas, controller_id, "button1", 240, 200)

            # Button 4 (white) - far right
            self.add_mapping_button(canvas, controller_id, "button4", 330, 200)

            # Left Joystick
            canvas.create_oval(70, 70, 130, 130, outline="yellow", width=2)
            self.add_mapping_button(canvas, controller_id, "joystick1_up", 100, 60, "↑")
            self.add_mapping_button(
                canvas, controller_id, "joystick1_down", 100, 140, "↓"
            )
            self.add_mapping_button(
                canvas, controller_id, "joystick1_left", 60, 100, "←"
            )
            self.add_mapping_button(
                canvas, controller_id, "joystick1_right", 140, 100, "→"
            )

            # Right Joystick
            canvas.create_oval(270, 70, 330, 130, outline="yellow", width=2)
            self.add_mapping_button(canvas, controller_id, "joystick2_up", 300, 60, "↑")
            self.add_mapping_button(
                canvas, controller_id, "joystick2_down", 300, 140, "↓"
            )
            self.add_mapping_button(
                canvas, controller_id, "joystick2_left", 260, 100, "←"
            )
            self.add_mapping_button(
                canvas, controller_id, "joystick2_right", 340, 100, "→"
            )
        else:
            # If no image, create a simple grid layout
            mapping_frame = ttk.LabelFrame(
                self.controller_map_frame, text="Button Mapping"
            )
            mapping_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Buttons
            ttk.Label(mapping_frame, text="Button 1:").grid(
                row=0, column=0, sticky=tk.W, padx=5, pady=5
            )
            self.add_text_mapping_button(
                mapping_frame, controller_id, "button1", row=0, column=1
            )

            ttk.Label(mapping_frame, text="Button 2:").grid(
                row=1, column=0, sticky=tk.W, padx=5, pady=5
            )
            self.add_text_mapping_button(
                mapping_frame, controller_id, "button2", row=1, column=1
            )

            ttk.Label(mapping_frame, text="Button 3:").grid(
                row=2, column=0, sticky=tk.W, padx=5, pady=5
            )
            self.add_text_mapping_button(
                mapping_frame, controller_id, "button3", row=2, column=1
            )

            ttk.Label(mapping_frame, text="Button 4:").grid(
                row=3, column=0, sticky=tk.W, padx=5, pady=5
            )
            self.add_text_mapping_button(
                mapping_frame, controller_id, "button4", row=3, column=1
            )

            # Joystick 1
            ttk.Label(mapping_frame, text="Left Joystick:").grid(
                row=4, column=0, sticky=tk.W, padx=5, pady=5
            )
            joystick1_frame = ttk.Frame(mapping_frame)
            joystick1_frame.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)

            ttk.Label(joystick1_frame, text="Up:").grid(row=0, column=1)
            self.add_text_mapping_button(
                joystick1_frame, controller_id, "joystick1_up", row=0, column=2
            )

            ttk.Label(joystick1_frame, text="Down:").grid(row=2, column=1)
            self.add_text_mapping_button(
                joystick1_frame, controller_id, "joystick1_down", row=2, column=2
            )

            ttk.Label(joystick1_frame, text="Left:").grid(row=1, column=0)
            self.add_text_mapping_button(
                joystick1_frame, controller_id, "joystick1_left", row=1, column=1
            )

            ttk.Label(joystick1_frame, text="Right:").grid(row=1, column=2)
            self.add_text_mapping_button(
                joystick1_frame, controller_id, "joystick1_right", row=1, column=3
            )

            # Joystick 2
            ttk.Label(mapping_frame, text="Right Joystick:").grid(
                row=5, column=0, sticky=tk.W, padx=5, pady=5
            )
            joystick2_frame = ttk.Frame(mapping_frame)
            joystick2_frame.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)

            ttk.Label(joystick2_frame, text="Up:").grid(row=0, column=1)
            self.add_text_mapping_button(
                joystick2_frame, controller_id, "joystick2_up", row=0, column=2
            )

            ttk.Label(joystick2_frame, text="Down:").grid(row=2, column=1)
            self.add_text_mapping_button(
                joystick2_frame, controller_id, "joystick2_down", row=2, column=2
            )

            ttk.Label(joystick2_frame, text="Left:").grid(row=1, column=0)
            self.add_text_mapping_button(
                joystick2_frame, controller_id, "joystick2_left", row=1, column=1
            )

            ttk.Label(joystick2_frame, text="Right:").grid(row=1, column=2)
            self.add_text_mapping_button(
                joystick2_frame, controller_id, "joystick2_right", row=1, column=3
            )

        # Save button
        save_frame = ttk.Frame(self.controller_map_frame)
        save_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            save_frame,
            text="Save Mappings",
            command=lambda: self.save_controller_mappings(controller_id),
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(
            save_frame,
            text="Reset to Default",
            command=lambda: self.reset_controller_mappings(controller_id),
        ).pack(side=tk.RIGHT, padx=5)

    def add_mapping_button(self, canvas, controller_id, control_name, x, y, text=None):
        """Add a button on the canvas for mapping"""
        key = self.controllers[controller_id].key_mappings.get(control_name, "-")
        if text is None:
            text = key

        # Assign different colors to buttons
        fill_color = "red"  # Default color
        text_color = "white"  # Default text color

        # Set specific colors for the four main buttons
        if control_name == "button1":
            fill_color = "red"
        elif control_name == "button2":
            fill_color = "blue"
        elif control_name == "button3":
            fill_color = "yellow"
            text_color = "black"  # Better visibility on yellow background
        elif control_name == "button4":
            fill_color = "white"
            text_color = "black"  # Better visibility on white background

        # Only change color for the main buttons, not joystick direction buttons
        if not control_name.startswith("joystick"):
            btn_id = canvas.create_oval(
                x - 15,
                y - 15,
                x + 15,
                y + 15,
                fill=fill_color,
                outline="white",
                width=2,
            )
            text_id = canvas.create_text(
                x, y, text=text, fill=text_color, font=("Arial", 9, "bold")
            )
        else:
            # For joystick buttons, keep the original behavior (no fill)
            btn_id = canvas.create_oval(
                x - 15, y - 15, x + 15, y + 15, fill="", outline="white", width=2
            )
            text_id = canvas.create_text(
                x, y, text=text, fill="white", font=("Arial", 9, "bold")
            )

        def on_click(event):
            self.start_key_listening(controller_id, control_name, canvas, text_id)

        canvas.tag_bind(btn_id, "<Button-1>", on_click)
        canvas.tag_bind(text_id, "<Button-1>", on_click)

        self.mapping_buttons[(controller_id, control_name)] = (canvas, text_id)

    def add_text_mapping_button(self, parent, controller_id, control_name, row, column):
        """Add a button with text for mapping in a grid layout"""
        key = self.controllers[controller_id].key_mappings.get(control_name, "-")

        btn = ttk.Button(
            parent,
            text=key,
            width=6,
            command=lambda: self.start_key_listening(controller_id, control_name, btn),
        )
        btn.grid(row=row, column=column, padx=2, pady=2)

        self.mapping_buttons[(controller_id, control_name)] = (None, btn)

    def start_key_listening(
        self, controller_id, control_name, canvas_or_button, text_id=None
    ):
        """Start listening for a keypress to map to the control"""
        self.listening_for_key = True
        self.current_mapping_control = (controller_id, control_name)

        # Change button appearance to indicate listening state
        if canvas_or_button.__class__.__name__ == "Canvas":
            # Set appropriate text color for the question mark
            text_color = "yellow"
            if control_name == "button3" or control_name == "button4":
                text_color = "orange"  # Better visibility on yellow/white buttons

            canvas_or_button.itemconfig(text_id, text="?", fill=text_color)
        else:
            canvas_or_button.config(text="?", style="Listening.TButton")

        # Focus on this window to capture key events
        self.focus_set()

    def on_key_press(self, event):
        """Handle key press events for mapping"""
        if not self.listening_for_key or not self.current_mapping_control:
            return

        # Get the pressed key
        key = event.keysym.lower()

        # Update the mapping
        controller_id, control_name = self.current_mapping_control
        self.controllers[controller_id].key_mappings[control_name] = key

        # Update the button text
        canvas_or_button, text_id = self.mapping_buttons[self.current_mapping_control]
        if canvas_or_button.__class__.__name__ == "Canvas":
            # Determine appropriate text color based on button type
            text_color = "white"  # Default
            if control_name == "button3" or control_name == "button4":
                text_color = "black"
            # Only joysticks always have white text
            elif control_name.startswith("joystick"):
                text_color = "white"

            canvas_or_button.itemconfig(text_id, text=key, fill=text_color)
        else:
            text_id.config(text=key, style="TButton")

        # Reset the listening state
        self.listening_for_key = False
        self.current_mapping_control = None

    def save_controller_mappings(self, controller_id):
        """Save the controller mappings to a file"""
        controller = self.controllers[controller_id]
        controller.save_mappings()
        if self.settings_manager:
            # Also save as default if this is the first controller or user wants to
            response = messagebox.askyesno(
                "Save as Default",
                "Would you like to save these mappings as the default for new controllers?",
            )
            if response:
                self.settings_manager.save_default_mappings(controller.key_mappings)
        messagebox.showinfo("Success", "Mappings saved successfully")

    def reset_controller_mappings(self, controller_id):
        """Reset the controller mappings to default"""
        controller = self.controllers[controller_id]

        # Reset to default mappings using settings manager
        if self.settings_manager:
            controller.key_mappings = (
                self.settings_manager.load_default_mappings().copy()
            )
        else:
            controller.key_mappings = DEFAULT_MAPPINGS.copy()

        # Update all button texts
        for (cid, control_name), (canvas, text_id) in self.mapping_buttons.items():
            if cid == controller_id:
                key = controller.key_mappings.get(control_name, "-")
                if canvas.__class__.__name__ == "Canvas":
                    canvas.itemconfig(text_id, text=key)
                else:
                    text_id.config(text=key)

        messagebox.showinfo("Reset", "Mappings reset to default")

    def validate_port(self, value):
        """Validate port number - only allow digits and ensure it's in valid range"""
        # Empty value is allowed during editing
        if value == "":
            return True

        # Only allow digits
        if not value.isdigit():
            return False

        # Check valid port range (1-65535)
        try:
            port_num = int(value)
            return 1 <= port_num <= 65535
        except ValueError:
            return False

    def apply_settings(self):
        """Apply the MQTT settings - Kept for compatibility"""
        # This method is retained but no longer used since we removed the MQTT settings UI
        pass

    def get_local_ip(self):
        """Get the local IP address of this machine"""
        try:
            # Try multiple approaches to get a valid IP
            # First approach: connect to external service
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            # If we got a valid IP that's not localhost, return it
            if local_ip and local_ip != "127.0.0.1":
                return local_ip

            # Second approach: get all network interfaces
            for interface in socket.getaddrinfo(socket.gethostname(), None):
                ip = interface[4][0]
                # Skip localhost and IPv6 addresses
                if ip != "127.0.0.1" and ":" not in ip:
                    return ip

            # If all methods fail, return localhost
            return "127.0.0.1"

        except Exception as e:
            print(f"Error getting local IP: {e}")
            # Return localhost as fallback
            return "127.0.0.1"

    def load_mosquitto_settings(self):
        """Load saved Mosquitto settings from file"""
        config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
        config_path = os.path.join(config_dir, "mosquitto_settings.json")

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading Mosquitto settings: {e}")

        # Return default settings if file doesn't exist or there's an error
        return {"port": "1883"}

    def save_mosquitto_settings(self):
        """Save Mosquitto settings to file"""
        config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "mosquitto_settings.json")

        try:
            settings = {"port": self.mosquitto_port_entry.get()}

            with open(config_path, "w") as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving Mosquitto settings: {e}")
            return False

    # Deprecated but kept for compatibility
    def find_mosquitto(self):
        """Find the Mosquitto executable in the PATH"""
        mosquitto_exe = "mosquitto.exe" if sys.platform == "win32" else "mosquitto"

        # First try using shutil.which
        path = shutil.which(mosquitto_exe)
        if path:
            print(f"Found mosquitto using shutil.which at: {path}")
            return path

        # If that fails, try a more direct approach for Windows
        if sys.platform == "win32":
            # Common installation paths
            common_paths = [
                "C:\\Program Files\\mosquitto\\mosquitto.exe",
                "C:\\Program Files (x86)\\mosquitto\\mosquitto.exe",
                os.path.join(
                    os.environ.get("ProgramFiles", ""), "mosquitto", "mosquitto.exe"
                ),
                os.path.join(
                    os.environ.get("ProgramFiles(x86)", ""),
                    "mosquitto",
                    "mosquitto.exe",
                ),
            ]

            # Check each path
            for path in common_paths:
                if os.path.exists(path) and os.path.isfile(path):
                    print(f"Found mosquitto at common path: {path}")
                    return path

            # Try searching in PATH manually
            for path_dir in os.environ.get("PATH", "").split(os.pathsep):
                exe_path = os.path.join(path_dir, mosquitto_exe)
                if os.path.exists(exe_path) and os.path.isfile(exe_path):
                    print(f"Found mosquitto in PATH at: {exe_path}")
                    return exe_path

        # If we get here, we couldn't find mosquitto
        print("Could not find mosquitto in PATH or common locations")
        return None

    # Deprecated but kept for compatibility
    def browse_for_mosquitto(self):
        """Open a file dialog to browse for the Mosquitto executable"""
        file_types = (
            [("Executable files", "*.exe")]
            if sys.platform == "win32"
            else [("All files", "*")]
        )
        initial_dir = (
            "C:\\Program Files\\mosquitto" if sys.platform == "win32" else "/usr/bin"
        )

        # Show file dialog
        mosquitto_path = filedialog.askopenfilename(
            title="Select Mosquitto Executable",
            initialdir=initial_dir,
            filetypes=file_types,
        )

        # If a file was selected, update the entry field
        if mosquitto_path:
            self.mosquitto_path_entry.delete(0, tk.END)
            self.mosquitto_path_entry.insert(0, mosquitto_path)

    def is_mqtt_server_running(self):
        """Check if MQTT server (Mosquitto) is already running"""
        try:
            # If our server is running, return True
            if self.server_running and self.mosquitto_process is not None:
                return True

            # Get port from UI or use default
            port = (
                int(self.mosquitto_port_entry.get())
                if self.mosquitto_port_entry.get()
                else 1883
            )

            # Try to check if a server is running on the MQTT port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)  # 1 second timeout
            result = s.connect_ex(("localhost", port))
            s.close()

            # If result is 0, the port is open and likely has an MQTT server
            return result == 0
        except Exception as e:
            print(f"Error checking MQTT server: {e}")
            return False

    def toggle_mosquitto_server(self):
        """Start or stop the Mosquitto server"""
        if self.server_running:
            # Stop the server
            try:
                # Disconnect MQTT client if it's connected
                if hasattr(self, "local_mqtt_client") and self.local_mqtt_client:
                    try:
                        self.local_mqtt_client.loop_stop()
                        self.local_mqtt_client.disconnect()
                    except Exception as mqtt_e:
                        print(f"Error disconnecting MQTT client: {mqtt_e}")

                # Stop Mosquitto process
                if self.mosquitto_process:
                    if sys.platform == "win32":
                        subprocess.run(
                            [
                                "taskkill",
                                "/F",
                                "/T",
                                "/PID",
                                str(self.mosquitto_process.pid),
                            ],
                            capture_output=True,
                            check=False,
                        )
                    else:
                        self.mosquitto_process.terminate()
                        self.mosquitto_process.wait(timeout=5)
                else:
                    # If we don't have the process but server is running, try to kill all mosquitto instances
                    if sys.platform == "win32":
                        subprocess.run(
                            ["taskkill", "/F", "/IM", "mosquitto.exe"],
                            capture_output=True,
                            check=False,
                        )
                    else:
                        subprocess.run(
                            ["pkill", "mosquitto"], capture_output=True, check=False
                        )

                # Update state and UI
                self.mosquitto_process = None
                self.server_running = False
                self.run_button.config(text="Run Mosquitto")
                self.update_server_status(False)
                self.update_mqtt_status(False)
                self.mosquitto_port_entry.config(state="normal")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop Mosquitto: {e}")
                return
        else:
            # Start the server
            try:
                # Validate port
                port = self.mosquitto_port_entry.get()
                if not port or not port.isdigit():
                    messagebox.showerror(
                        "Error", "Please enter a valid port number (1-65535)"
                    )
                    return

                port_num = int(port)
                if port_num < 1 or port_num > 65535:
                    messagebox.showerror("Error", "Port must be between 1 and 65535")
                    return

                # Check if port is already in use
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)
                    result = s.connect_ex(("localhost", port_num))
                    s.close()
                    if result == 0:
                        messagebox.showerror(
                            "Error", f"Port {port_num} is already in use"
                        )
                        return
                except:
                    pass

                # Save current port setting
                self.save_mosquitto_settings()

                # Start Mosquitto with the specified port using the -v (verbose) flag
                try:
                    self.mosquitto_process = subprocess.Popen(
                        ["mosquitto", "-v", "-p", port],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=(
                            subprocess.CREATE_NO_WINDOW
                            if sys.platform == "win32"
                            else 0
                        ),
                    )

                    # Wait a moment to verify Mosquitto started successfully
                    time.sleep(1)
                    if not self.is_mqtt_server_running():
                        raise Exception("Failed to start Mosquitto server")

                    # Update UI
                    self.server_running = True
                    self.run_button.config(text="Stop Mosquitto")
                    self.update_server_status(True)
                    self.mosquitto_port_entry.config(state="readonly")

                    # Wait for Mosquitto to initialize before connecting
                    self.after(2000, self.connect_mqtt)

                except FileNotFoundError:
                    messagebox.showerror(
                        "Error",
                        "Mosquitto executable not found. Make sure 'mosquitto' is in your system PATH.",
                    )
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to start Mosquitto: {e}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to start Mosquitto: {e}")

    def connect_mqtt(self):
        """Connect to the MQTT server after Mosquitto has been started"""
        if not hasattr(self, "local_mqtt_client") or not self.local_mqtt_client:
            return

        try:
            # Get port from UI or use default
            port = (
                int(self.mosquitto_port_entry.get())
                if self.mosquitto_port_entry.get()
                else 1883
            )

            # Verify Mosquitto is running on the specified port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(("localhost", port))
            s.close()

            if result != 0:
                print(f"Mosquitto not running on port {port}")
                self.update_mqtt_status(False)
                return

            # Connect to MQTT server
            self.local_mqtt_client.connect("localhost", port, 60)
            self.local_mqtt_client.loop_start()

            # Update status
            self.update_mqtt_status(True)
            print(f"Connected to MQTT server on port {port}")
        except Exception as e:
            print(f"Failed to connect to MQTT server: {e}")
            self.update_mqtt_status(False)

    def set_connection_status(self, connected):
        """Update the UI to show MQTT connection status."""
        # Update using the new unified status indicators
        self.update_mqtt_status(connected)

    def refresh_ip_display(self):
        """Refresh the IP display with current local IP"""
        local_ip = self.get_local_ip()
        self.ip_display.config(state="normal")
        self.ip_display.delete(0, tk.END)
        self.ip_display.insert(0, local_ip)
        self.ip_display.config(state="readonly")

    def on_closing(self):
        """Handle window closing event"""
        self.destroy()
