import os
import sys
import tkinter as tk
from tkinter import ttk

from gui.controllers_tab import setup_controllers_tab
from gui.settings_tab import setup_settings_tab
from gui.controller_mapping import setup_controller_mapping
from gui.logs_tab import setup_logs_tab, add_log
from controller.game_controller import DEFAULT_MAPPINGS


class GameControllerGUI(tk.Tk):
    def __init__(self, controllers):
        super().__init__()

        self.title("Bat Controller Configuration")
        self.geometry("800x600")
        self.controllers = controllers
        self.mqtt_client = None

        # Create a notebook with tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create the controllers tab
        self.controllers_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.controllers_frame, text="Controllers")
        setup_controllers_tab(self)

        # Create the settings tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        setup_settings_tab(self)

        # Create the logs tab
        self.logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.logs_frame, text="Logs")
        setup_logs_tab(self)

        # Variable to keep track of the currently selected controller
        self.selected_controller_id = None
        self.controller_frames = {}

        # Load the bat logo
        image_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets",
            "bat-black-silhouette-with-opened-wings.png",
        )
        if os.path.exists(image_path):
            try:
                from PIL import Image, ImageTk

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

    def update_controllers(self, controllers):
        """Update the list of controllers"""
        self.controllers = controllers
        self.refresh_controllers()
        add_log(self, f"Controllers updated. Total controllers: {len(controllers)}")

    def refresh_controllers(self):
        """Refresh the listbox of controllers"""
        if hasattr(self, "controllers_listbox"):
            self.controllers_listbox.delete(0, tk.END)

            if not self.controllers:
                self.status_label.config(text="No controllers connected")
                add_log(self, "No controllers connected", "WARNING")
            else:
                self.status_label.config(
                    text=f"{len(self.controllers)} controller(s) connected"
                )
                add_log(self, f"{len(self.controllers)} controller(s) connected")

                for controller_id, controller in sorted(
                    self.controllers.items(), key=lambda x: x[0]
                ):
                    self.controllers_listbox.insert(
                        tk.END, f"{controller.name} (ID: {controller_id})"
                    )
                    add_log(
                        self,
                        f"Controller found: {controller.name} (ID: {controller_id})",
                    )

    def on_controller_select(self, event):
        """Handle selection of a controller from the listbox"""
        if self.controllers_listbox.curselection():
            index = self.controllers_listbox.curselection()[0]
            controller_id = list(self.controllers.keys())[index]
            self.selected_controller_id = controller_id
            add_log(
                self,
                f"Selected controller: {self.controllers[controller_id].name} (ID: {controller_id})",
            )

    def configure_selected_controller(self):
        """Open the configuration tab for the selected controller"""
        if not self.selected_controller_id:
            from tkinter import messagebox

            messagebox.showinfo("Select Controller", "Please select a controller first")
            add_log(
                self,
                "Attempted to configure controller without selecting one",
                "WARNING",
            )
            return

        # Close existing controller tab if open
        for tab in self.notebook.tabs():
            tab_name = self.notebook.tab(tab, "text")
            if tab_name.startswith("Controller "):
                self.notebook.forget(tab)

        # Create new controller tab
        from gui.controller_mapping import setup_controller_mapping

        controller_id = self.selected_controller_id
        controller_name = self.controllers[controller_id].name

        self.controller_map_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.controller_map_frame, text=f"{controller_name} Config")
        self.notebook.select(self.controller_map_frame)

        # Setup controller mapping UI
        setup_controller_mapping(self, controller_id)
        add_log(
            self,
            f"Opened configuration for controller: {controller_name} (ID: {controller_id})",
        )

    def on_key_press(self, event):
        """Handle key press events for mapping"""
        if not self.listening_for_key:
            return

        if (
            not hasattr(self, "current_mapping_control")
            or not self.current_mapping_control
        ):
            return

        key_char = event.char
        key_sym = event.keysym.lower()

        # Choose the most appropriate representation of the key
        if key_char and ord(key_char) >= 32 and ord(key_char) <= 126:
            key = key_char
        else:
            key = key_sym

        # Update the key mapping
        controller_id, control_name = self.current_mapping_control
        self.controllers[controller_id].update_key_mapping(control_name, key)
        add_log(
            self,
            f"Updated key mapping for {control_name} to '{key}' on controller {controller_id}",
        )

        # Update the button text
        if (
            hasattr(self, "mapping_buttons")
            and (controller_id, control_name) in self.mapping_buttons
        ):
            button_info = self.mapping_buttons[(controller_id, control_name)]

            if "text_id" in button_info:
                # For canvas buttons
                canvas, text_id = button_info["canvas"], button_info["text_id"]
                canvas.itemconfig(text_id, text=key if key else "None")
            elif "button" in button_info:
                # For regular buttons
                button_info["button"].config(
                    text=f"{control_name.replace('_', ' ').title()}: {key}"
                )

        # Stop listening for keys
        self.listening_for_key = False
        self.current_mapping_control = None
