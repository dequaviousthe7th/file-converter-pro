#!/bin/bash
# File Converter Pro - Installer (macOS / Linux)

cd "$(dirname "$0")"

# Check for Python 3
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo ""
    echo "  ERROR: Python 3 is not installed."
    echo ""
    echo "  Install Python 3.8+ from: https://www.python.org/downloads/"
    echo "  Or use your package manager:"
    echo "    macOS:  brew install python3"
    echo "    Ubuntu: sudo apt install python3 python3-venv python3-tk"
    echo ""
    exit 1
fi

echo "Using: $($PYTHON --version)"
$PYTHON install.py
