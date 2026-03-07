#!/usr/bin/env python3
"""
Build a standalone Setup.exe installer for File Converter Pro.
Run this once to create a distributable installer.

Requires: pip install pyinstaller
Usage: python build_installer.py
Output: dist/File Converter Pro Setup.exe
"""

import subprocess
import sys
import shutil
from pathlib import Path

APP_DIR = Path(__file__).parent.resolve()
DIST_DIR = APP_DIR / "dist"


def main():
    print("=" * 50)
    print("  File Converter Pro - Build Installer")
    print("=" * 50)
    print()

    # Check for PyInstaller
    try:
        import PyInstaller
        print(f"  PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("  PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"],
                       check=True)
        print("  PyInstaller installed.")

    print()
    print("  Building installer...")
    print()

    # Collect data files to bundle
    datas = [
        (str(APP_DIR / "assets"), "assets"),
        (str(APP_DIR / "backend"), "backend"),
        (str(APP_DIR / "utils"), "utils"),
        (str(APP_DIR / "config.py"), "."),
        (str(APP_DIR / "requirements.txt"), "."),
        (str(APP_DIR / "app.py"), "."),
        (str(APP_DIR / "app_simple.py"), "."),
        (str(APP_DIR / "START.bat"), "."),
        (str(APP_DIR / "START_SIMPLE.bat"), "."),
    ]

    add_data_args = []
    sep = ";" if sys.platform == "win32" else ":"
    for src, dst in datas:
        if Path(src).exists():
            add_data_args.extend(["--add-data", f"{src}{sep}{dst}"])

    icon_path = APP_DIR / "assets" / "logo.ico"
    icon_arg = ["--icon", str(icon_path)] if icon_path.exists() else []

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "File Converter Pro Setup",
        *icon_arg,
        *add_data_args,
        "--clean",
        str(APP_DIR / "install.py"),
    ]

    result = subprocess.run(cmd, cwd=str(APP_DIR))

    if result.returncode == 0:
        print()
        print("=" * 50)
        print("  BUILD SUCCESSFUL!")
        print(f"  Output: dist/File Converter Pro Setup.exe")
        print("=" * 50)
    else:
        print()
        print("  BUILD FAILED. Check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
