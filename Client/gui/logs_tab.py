import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime


def setup_logs_tab(app):
    """Setup the logs tab in the GUI"""

    # Create main frame for logs
    logs_frame = app.logs_frame

    # Create a text widget for displaying logs with scrollbar
    log_text = scrolledtext.ScrolledText(logs_frame, wrap=tk.WORD, height=20)
    log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Store the text widget reference in the app for later use
    app.log_text = log_text

    # Create control buttons frame
    control_frame = ttk.Frame(logs_frame)
    control_frame.pack(fill=tk.X, padx=10, pady=5)

    # Add clear button
    clear_button = ttk.Button(
        control_frame, text="Clear Logs", command=lambda: clear_logs(app)
    )
    clear_button.pack(side=tk.RIGHT, padx=5)

    # Add save button
    save_button = ttk.Button(
        control_frame, text="Save Logs", command=lambda: save_logs(app)
    )
    save_button.pack(side=tk.RIGHT, padx=5)


def add_log(app, message, level="INFO"):
    """Add a new log entry to the log display"""
    if not hasattr(app, "log_text"):
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"

    app.log_text.insert(tk.END, log_entry)
    app.log_text.see(tk.END)  # Auto-scroll to the bottom


def clear_logs(app):
    """Clear all logs from the display"""
    if hasattr(app, "log_text"):
        app.log_text.delete(1.0, tk.END)


def save_logs(app):
    """Save logs to a file"""
    if not hasattr(app, "log_text"):
        return

    from tkinter import filedialog
    import os

    # Get the current timestamp for the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"controller_logs_{timestamp}.txt"

    # Open file dialog
    filename = filedialog.asksaveasfilename(
        initialfile=default_filename,
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )

    if filename:
        try:
            with open(filename, "w") as f:
                f.write(app.log_text.get(1.0, tk.END))
            add_log(app, f"Logs saved to {filename}", "INFO")
        except Exception as e:
            add_log(app, f"Error saving logs: {e}", "ERROR")
