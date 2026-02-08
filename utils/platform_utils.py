"""
Cross-platform utilities for File Converter Pro.
Handles OS-specific operations like opening folders and finding fonts.
"""

import os
import sys
import subprocess
import platform


def open_folder(path):
    """Open a folder in the system file explorer. Cross-platform."""
    path = str(path)
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        # Last resort fallback
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(path)}")


def open_file(path):
    """Open a file with the system default application. Cross-platform."""
    path = str(path)
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(path)}")


def find_system_font():
    """Find a suitable system font path for image text rendering."""
    system = platform.system()

    font_paths = []
    if system == "Windows":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        font_paths = [
            os.path.join(windir, "Fonts", "segoeui.ttf"),
            os.path.join(windir, "Fonts", "arial.ttf"),
            os.path.join(windir, "Fonts", "calibri.ttf"),
            os.path.join(windir, "Fonts", "consola.ttf"),
        ]
    elif system == "Darwin":
        font_paths = [
            "/System/Library/Fonts/SFPro.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/SFNSMono.ttf",
        ]
    else:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]

    for path in font_paths:
        if os.path.exists(path):
            return path
    return None


def check_ffmpeg():
    """Check if ffmpeg is installed and accessible."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_libreoffice():
    """Check if LibreOffice is installed and accessible."""
    try:
        result = subprocess.run(
            ["libreoffice", "--version"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
