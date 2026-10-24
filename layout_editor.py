"""Direct launcher for The Daily Prophet Interactive Layout Slot Editor.

Usage:
    python layout_editor.py
"""

import sys
import os

# Set Windows AppUserModelID so taskbar displays the custom app icon
if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ca.zandercraft.dailyprophet.editor")
    except Exception:
        pass

import customtkinter as ctk

# Ensure workspace root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from daily_prophet.gui.layout_editor_window import LayoutEditorWindow


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    root.withdraw()  # Hide root window, show editor directly

    editor = LayoutEditorWindow(root, initial_layout="layout_1", base_dir=".")
    editor.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
