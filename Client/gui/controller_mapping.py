import os
import tkinter as tk
from tkinter import ttk


def setup_controller_mapping(app, controller_id):
    """Set up the UI for mapping controller buttons to keys"""
    controller = app.controllers[controller_id]
    
    # Controller name frame
    name_frame = ttk.Frame(app.controller_map_frame)
    name_frame.pack(fill=tk.X, padx=10, pady=5)
    
    ttk.Label(name_frame, text="Controller Name:").pack(side=tk.LEFT, padx=5)
    name_var = tk.StringVar(value=controller.name)
    name_entry = ttk.Entry(name_frame, textvariable=name_var, width=30)
    name_entry.pack(side=tk.LEFT, padx=5)
    
    def update_name():
        """Update the controller name when the entry changes"""
        controller.name = name_var.get()
        controller.save_mappings()
        # Update the tab name
        tab_id = app.notebook.select()
        app.notebook.tab(tab_id, text=f"{controller.name} Config")
    
    ttk.Button(name_frame, text="Update Name", command=update_name).pack(side=tk.LEFT, padx=5)
    
    # Create a frame for the controller image and mapping buttons
    controller_frame = ttk.Frame(app.controller_map_frame)
    controller_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # If we have a controller image, use it for visual mapping
    if hasattr(app, "controller_photo") and app.controller_photo:
        # Create a canvas for the image and buttons
        canvas = tk.Canvas(controller_frame, width=400, height=300)
        canvas.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Add the controller image
        canvas.create_image(200, 150, image=app.controller_photo)
        
        # Add mapping buttons for standard controller buttons
        add_mapping_button(app, canvas, controller_id, "button1", 320, 100, "1")
        add_mapping_button(app, canvas, controller_id, "button2", 340, 120, "2")
        add_mapping_button(app, canvas, controller_id, "button3", 360, 140, "3")
        add_mapping_button(app, canvas, controller_id, "button4", 380, 160, "4")
        
        # Add mapping for joysticks
        # Joystick 1 (left)
        add_mapping_button(app, canvas, controller_id, "joystick1_up", 60, 100, "↑")
        add_mapping_button(app, canvas, controller_id, "joystick1_down", 60, 140, "↓")
        add_mapping_button(app, canvas, controller_id, "joystick1_left", 40, 120, "←")
        add_mapping_button(app, canvas, controller_id, "joystick1_right", 80, 120, "→")
        
        # Joystick 2 (right)
        add_mapping_button(app, canvas, controller_id, "joystick2_up", 300, 100, "↑")
        add_mapping_button(app, canvas, controller_id, "joystick2_down", 300, 140, "↓")
        add_mapping_button(app, canvas, controller_id, "joystick2_left", 280, 120, "←")
        add_mapping_button(app, canvas, controller_id, "joystick2_right", 320, 120, "→")
    else:
        # If no image, use a simple grid layout
        mapping_frame = ttk.LabelFrame(controller_frame, text="Button Mappings")
        mapping_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a grid for buttons
        ttk.Label(mapping_frame, text="Button").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(mapping_frame, text="Key").grid(row=0, column=1, padx=5, pady=5)
        
        # Add text buttons for each mapping
        row = 1
        for control_name in sorted(controller.key_mappings.keys()):
            add_text_mapping_button(app, mapping_frame, controller_id, control_name, row, 0)
            row += 1
    
    # Add buttons to save/reset mappings
    button_frame = ttk.Frame(app.controller_map_frame)
    button_frame.pack(fill=tk.X, padx=10, pady=10)
    
    ttk.Button(
        button_frame, 
        text="Save Mappings", 
        command=lambda: save_controller_mappings(app, controller_id)
    ).pack(side=tk.LEFT, padx=5)
    
    ttk.Button(
        button_frame, 
        text="Reset to Default", 
        command=lambda: reset_controller_mappings(app, controller_id)
    ).pack(side=tk.RIGHT, padx=5)


def add_mapping_button(app, canvas, controller_id, control_name, x, y, text=None):
    """Add a button on the canvas for mapping"""
    # Create a circle for the button
    circle = canvas.create_oval(x-15, y-15, x+15, y+15, fill="lightgrey", outline="black")
    
    # Show current mapping or default text
    current_key = app.controllers[controller_id].key_mappings.get(control_name, "")
    display_text = current_key if current_key else (text if text else "")
    
    # Add text for the button
    text_id = canvas.create_text(x, y, text=display_text, font=("Arial", 9, "bold"))
    
    # Add click handler to start key mapping
    def on_click(event):
        # Only respond if the click is within the circle
        if (event.x - x)**2 + (event.y - y)**2 <= 15**2:
            start_key_listening(app, controller_id, control_name, canvas, text_id)
    
    canvas.tag_bind(circle, "<Button-1>", on_click)
    canvas.tag_bind(text_id, "<Button-1>", on_click)
    
    # Store reference to the button for updating later
    if not hasattr(app, "mapping_buttons"):
        app.mapping_buttons = {}
    app.mapping_buttons[(controller_id, control_name)] = {
        "canvas": canvas,
        "text_id": text_id,
    }


def add_text_mapping_button(app, parent, controller_id, control_name, row, column):
    """Add a button with text for mapping in a grid layout"""
    current_key = app.controllers[controller_id].key_mappings.get(control_name, "")
    
    # Create button with current mapping
    button_text = f"{control_name.replace('_', ' ').title()}: {current_key}"
    button = ttk.Button(
        parent, 
        text=button_text,
        command=lambda: start_key_listening(app, controller_id, control_name, button)
    )
    button.grid(row=row, column=column, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=2)
    
    # Store reference to the button for updating later
    if not hasattr(app, "mapping_buttons"):
        app.mapping_buttons = {}
    app.mapping_buttons[(controller_id, control_name)] = {"button": button}


def start_key_listening(app, controller_id, control_name, canvas_or_button, text_id=None):
    """Start listening for a keypress to map to the control"""
    app.listening_for_key = True
    app.current_mapping_control = (controller_id, control_name)
    
    # Update UI to show we're listening
    if text_id:  # Canvas button
        canvas = canvas_or_button
        canvas.itemconfig(text_id, text="Press\nKey")
    else:  # Regular button
        button = canvas_or_button
        button.config(text=f"Press a key for {control_name.replace('_', ' ').title()}")
        
    # Show a status message
    if hasattr(app, "status_label"):
        app.status_label.config(
            text=f"Press a key to map to {control_name.replace('_', ' ').title()}..."
        )


def save_controller_mappings(app, controller_id):
    """Save the controller mappings to a file"""
    app.controllers[controller_id].save_mappings()
    if hasattr(app, "status_label"):
        app.status_label.config(text="Mappings saved successfully")


def reset_controller_mappings(app, controller_id):
    """Reset the controller mappings to default"""
    from controller import DEFAULT_MAPPINGS
    
    # Reset mappings
    app.controllers[controller_id].key_mappings = DEFAULT_MAPPINGS.copy()
    app.controllers[controller_id].save_mappings()
    
    # Update UI
    if hasattr(app, "controller_map_frame"):
        # Refresh the controller mapping tab
        # First, get the current tab and controller
        tab_id = app.notebook.select()
        app.notebook.forget(tab_id)
        
        # Recreate the tab
        app.controller_map_frame = ttk.Frame(app.notebook)
        app.notebook.add(app.controller_map_frame, text=f"{app.controllers[controller_id].name} Config")
        app.notebook.select(app.controller_map_frame)
        
        # Setup controller mapping UI again
        setup_controller_mapping(app, controller_id)
        
    if hasattr(app, "status_label"):
        app.status_label.config(text="Mappings reset to default")
