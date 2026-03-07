#!/bin/bash
# Build File Converter Pro for macOS
# Run this on a Mac: ./installer/build_mac.sh
# Requires: Python 3.8+, pip

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "============================================"
echo "  File Converter Pro - macOS Build"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 not found. Install from https://python.org"
    exit 1
fi
echo "Python: $(python3 --version)"

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pyinstaller -q

echo ""
echo "Building Advanced UI..."
pyinstaller --noconfirm --onedir --windowed \
    --name "File Converter Pro" \
    --icon assets/logo.png \
    --add-data "assets:assets" \
    --add-data "backend:backend" \
    --add-data "utils:utils" \
    --add-data "config.py:." \
    --hidden-import customtkinter \
    --hidden-import PIL \
    --hidden-import tkinterdnd2 \
    --collect-all customtkinter \
    --collect-all tkinterdnd2 \
    app.py

echo ""
echo "Building Simple UI..."
pyinstaller --noconfirm --onedir --windowed \
    --name "File Converter Pro Simple" \
    --icon assets/logo.png \
    --add-data "assets:assets" \
    --add-data "backend:backend" \
    --add-data "utils:utils" \
    --add-data "config.py:." \
    --hidden-import PIL \
    --hidden-import tkinterdnd2 \
    --collect-all tkinterdnd2 \
    app_simple.py

# Create DMG-friendly structure
echo ""
echo "Packaging..."
DMG_DIR="dist/File Converter Pro"
mkdir -p "$DMG_DIR"

# Move the .app bundles
if [ -d "dist/File Converter Pro.app" ]; then
    mv "dist/File Converter Pro.app" "$DMG_DIR/"
fi
if [ -d "dist/File Converter Pro Simple.app" ]; then
    mv "dist/File Converter Pro Simple.app" "$DMG_DIR/"
fi

echo ""
echo "============================================"
echo "  BUILD COMPLETE!"
echo ""
echo "  Output: dist/File Converter Pro/"
echo ""
echo "  To create a DMG:"
echo "    hdiutil create -volname 'File Converter Pro' \\"
echo "      -srcfolder 'dist/File Converter Pro' \\"
echo "      -ov -format UDZO dist/FCP-Setup.dmg"
echo "============================================"
