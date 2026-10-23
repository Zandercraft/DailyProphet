"""Export engine for The Daily Prophet supporting both PDF and high-res Image export."""
import os
import shutil
import subprocess
import webbrowser
from typing import Optional, Tuple
from PIL import Image


def find_browser_executable() -> Optional[str]:
    """Locates Microsoft Edge or Google Chrome executable on the system."""
    potential_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in potential_paths:
        if os.path.isfile(path):
            return path

    for name in ["msedge", "chrome", "google-chrome", "chromium"]:
        which_path = shutil.which(name)
        if which_path and os.path.isfile(which_path):
            return which_path

    return None


def export_html_to_pdf(html_path: str, output_pdf_path: str, timeout: int = 20) -> Tuple[bool, str]:
    """Exports an HTML broadsheet directly to high-quality PDF.
    
    Returns (success: bool, message: str)
    """
    browser_exe = find_browser_executable()
    abs_html = os.path.abspath(html_path)
    abs_pdf = os.path.abspath(output_pdf_path)

    if not browser_exe:
        webbrowser.open(f"file:///{abs_html}")
        return False, "Chromium/Edge executable not detected. Opened newspaper in default browser for standard Print to PDF."

    cmd = [
        browser_exe,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={abs_pdf}",
        f"file:///{abs_html}",
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if os.path.isfile(abs_pdf) and os.path.getsize(abs_pdf) > 0:
            return True, f"Successfully exported PDF to: {abs_pdf}"
        else:
            return False, f"Browser PDF export failed. Error: {res.stderr.decode('utf-8', errors='ignore')}"
    except Exception as e:
        return False, f"PDF export failed: {str(e)}"


def _auto_trim_broadsheet(img: Image.Image, padding: int = 16) -> Image.Image:
    """Detects where the broadsheet content ends vertically and trims excess browser viewport whitespace."""
    try:
        import numpy as np

        arr = np.array(img)
        h, w = arr.shape[:2]
        if h < 200 or w < 200:
            return img

        # Sample bottom margin background color from bottom-center
        bg = arr[h - 6 : h, w // 2 - 20 : w // 2 + 20, :3].mean(axis=(0, 1))

        # Center vertical strip (where the broadsheet page resides)
        center_strip = arr[:, w // 2 - 50 : w // 2 + 50, :3]
        diff = np.abs(center_strip - bg).max(axis=(1, 2))

        # Find rows with meaningful content or borders distinct from empty viewport
        content_rows = np.where(diff > 12)[0]
        if len(content_rows) == 0:
            return img

        max_y = min(h, int(content_rows[-1]) + padding)
        if max_y < h - 10:
            return img.crop((0, 0, w, max_y))
    except Exception:
        pass
    return img


def export_html_to_image(
    html_path: str,
    output_image_path: str,
    width: int = 1080,
    height: int = 3000,
    timeout: int = 20,
) -> Tuple[bool, str]:
    """Exports an HTML broadsheet directly to an ultra high-resolution PNG or JPG image.
    
    Returns (success: bool, message: str)
    """
    browser_exe = find_browser_executable()
    abs_html = os.path.abspath(html_path)
    abs_out = os.path.abspath(output_image_path)

    if not browser_exe:
        return False, "Chromium or Edge browser executable not found on system."

    # Edge headless screenshot saves directly to a PNG
    temp_screenshot = abs_out if abs_out.lower().endswith(".png") else abs_out + ".temp.png"

    cmd = [
        browser_exe,
        "--headless=new",
        "--disable-gpu",
        f"--screenshot={temp_screenshot}",
        f"--window-size={width},{height}",
        f"file:///{abs_html}",
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if not os.path.isfile(temp_screenshot) or os.path.getsize(temp_screenshot) == 0:
            return False, f"Screenshot capture failed. Details: {res.stderr.decode('utf-8', errors='ignore')}"

        # Post-process with Pillow: crop cleanly to broadsheet margins if needed or convert format
        with Image.open(temp_screenshot) as img:
            trimmed = _auto_trim_broadsheet(img)
            # If user wanted JPEG, convert mode to RGB and save
            ext = os.path.splitext(abs_out)[1].lower()
            if ext in [".jpg", ".jpeg"]:
                rgb_img = trimmed.convert("RGB")
                rgb_img.save(abs_out, "JPEG", quality=95)
                if temp_screenshot != abs_out and os.path.isfile(temp_screenshot):
                    os.remove(temp_screenshot)
            else:
                trimmed.save(abs_out, "PNG", optimize=True)
                if temp_screenshot != abs_out and os.path.isfile(temp_screenshot):
                    os.remove(temp_screenshot)

        return True, f"Successfully exported broadsheet image to: {abs_out}"
    except Exception as e:
        return False, f"Image export failed: {str(e)}"
