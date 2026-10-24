"""Main launcher for The Daily Prophet application."""

import sys
import os

# Set Windows AppUserModelID so taskbar displays the custom app icon
if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ca.zandercraft.dailyprophet.editor")
    except Exception:
        pass

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from daily_prophet.gui import MainWindow


def main():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
