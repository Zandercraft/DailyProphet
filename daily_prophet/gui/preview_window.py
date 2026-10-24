"""Newspaper preview integration."""
import os


def open_image_preview(image_path: str) -> bool:
    """Opens the rendered high-resolution newspaper in the system default viewer."""
    try:
        if os.path.exists(image_path):
            os.startfile(os.path.abspath(image_path))
            return True
    except Exception:
        pass
    return False
