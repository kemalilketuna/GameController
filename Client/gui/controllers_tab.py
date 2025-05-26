import tkinter as tk
from tkinter import ttk


def setup_controllers_tab(app):
    """Set up the controllers tab with a list of connected controllers"""
    # Create a frame for the controller list
    app.controllers_list_frame = ttk.LabelFrame(
        app.controllers_frame, text="Connected Controllers"
    )
    app.controllers_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Create a listbox for the controllers
    app.controllers_listbox = tk.Listbox(app.controllers_list_frame, height=10)
    app.controllers_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    app.controllers_listbox.bind("<<ListboxSelect>>", app.on_controller_select)

    # Add a refresh button
    app.refresh_button = ttk.Button(
        app.controllers_list_frame,
        text="Refresh",
        command=app.refresh_controllers,
    )
    app.refresh_button.pack(side=tk.LEFT, padx=5, pady=5)

    # Add a configure button
    app.configure_button = ttk.Button(
        app.controllers_list_frame,
        text="Configure",
        command=app.configure_selected_controller,
    )
    app.configure_button.pack(side=tk.RIGHT, padx=5, pady=5)

    # Status label
    app.status_label = ttk.Label(
        app.controllers_frame, text="Waiting for controllers..."
    )
    app.status_label.pack(pady=5)

    # Initial refresh
    app.refresh_controllers()
