"""Newspaper preview integration supporting embedded Edge WebView window and browser."""
import os
import sys
import tempfile
import webbrowser
import subprocess


def open_image_preview(image_path: str) -> bool:
    """Opens the rendered high-resolution newspaper in the system default viewer."""
    try:
        if os.path.exists(image_path):
            os.startfile(os.path.abspath(image_path))
            return True
    except Exception:
        pass
    return False


def save_temp_preview(html_content: str) -> str:
    """Saves the newspaper HTML to a persistent temporary file and returns its path."""
    temp_dir = tempfile.gettempdir()
    preview_path = os.path.join(temp_dir, "daily_prophet_preview.html")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return preview_path


def open_in_browser(html_content: str) -> str:
    """Opens the broadsheet in the user's default web browser."""
    path = save_temp_preview(html_content)
    webbrowser.open(f"file:///{os.path.abspath(path)}")
    return path


def open_webview_window(html_content: str, title: str = "The Daily Prophet - Broadsheet Preview") -> bool:
    """Spawns an isolated WebView window displaying the newspaper."""
    path = save_temp_preview(html_content)
    # Launch in a lightweight background process to prevent event-loop conflicts with Tkinter
    script = f"""
import sys
import webview

def run():
    path = {repr(path)}
    window = webview.create_window({repr(title)}, url=f"file:///{{path}}", width=1200, height=900)
    webview.start()

if __name__ == '__main__':
    run()
"""
    try:
        subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        # Fallback to browser
        webbrowser.open(f"file:///{os.path.abspath(path)}")
        return False
