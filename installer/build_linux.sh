#!/bin/bash
# Build File Converter Pro for Linux
# Run this on Linux: ./installer/build_linux.sh
# Requires: Python 3.8+, pip

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "============================================"
echo "  File Converter Pro - Linux Build"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 not found."
    echo "Install: sudo apt install python3 python3-pip python3-venv"
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
pyinstaller --noconfirm --onedir \
    --name "file-converter-pro" \
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
pyinstaller --noconfirm --onedir \
    --name "file-converter-pro-simple" \
    --icon assets/logo.png \
    --add-data "assets:assets" \
    --add-data "backend:backend" \
    --add-data "utils:utils" \
    --add-data "config.py:." \
    --hidden-import PIL \
    --hidden-import tkinterdnd2 \
    --collect-all tkinterdnd2 \
    app_simple.py

# Create .desktop files
echo ""
echo "Creating .desktop entries..."

cat > "dist/file-converter-pro/File Converter Pro.desktop" << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=File Converter Pro (Advanced)
Comment=Convert files - Modern dark theme
Exec=%INSTALL_DIR%/file-converter-pro
Path=%INSTALL_DIR%
Icon=%INSTALL_DIR%/assets/logo.png
Terminal=false
Categories=Utility;FileTools;
DESKTOP

cat > "dist/file-converter-pro-simple/File Converter Pro Simple.desktop" << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=File Converter Pro (Simple)
Comment=Convert files - Classic lightweight
Exec=%INSTALL_DIR%/file-converter-pro-simple
Path=%INSTALL_DIR%
Icon=%INSTALL_DIR%/assets/logo.png
Terminal=false
Categories=Utility;FileTools;
DESKTOP

# Create install script
cat > "dist/install.sh" << 'INSTALL'
#!/bin/bash
# Install File Converter Pro on Linux
set -e

INSTALL_DIR="$HOME/.local/share/file-converter-pro"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "Installing File Converter Pro..."

mkdir -p "$INSTALL_DIR/Advanced" "$INSTALL_DIR/Simple" "$BIN_DIR" "$DESKTOP_DIR"

# Copy files
cp -r file-converter-pro/* "$INSTALL_DIR/Advanced/"
cp -r file-converter-pro-simple/* "$INSTALL_DIR/Simple/"

# Make executable
chmod +x "$INSTALL_DIR/Advanced/file-converter-pro"
chmod +x "$INSTALL_DIR/Simple/file-converter-pro-simple"

# Create symlinks in PATH
ln -sf "$INSTALL_DIR/Advanced/file-converter-pro" "$BIN_DIR/file-converter-pro"
ln -sf "$INSTALL_DIR/Simple/file-converter-pro-simple" "$BIN_DIR/file-converter-pro-simple"

# Create .desktop entries
cat > "$DESKTOP_DIR/file-converter-pro.desktop" << EOF
[Desktop Entry]
Type=Application
Name=File Converter Pro (Advanced)
Comment=Convert files - Modern dark theme
Exec=$INSTALL_DIR/Advanced/file-converter-pro
Path=$INSTALL_DIR/Advanced
Icon=$INSTALL_DIR/Advanced/assets/logo.png
Terminal=false
Categories=Utility;FileTools;
EOF

cat > "$DESKTOP_DIR/file-converter-pro-simple.desktop" << EOF
[Desktop Entry]
Type=Application
Name=File Converter Pro (Simple)
Comment=Convert files - Classic lightweight
Exec=$INSTALL_DIR/Simple/file-converter-pro-simple
Path=$INSTALL_DIR/Simple
Icon=$INSTALL_DIR/Simple/assets/logo.png
Terminal=false
Categories=Utility;FileTools;
EOF

echo ""
echo "Installed to: $INSTALL_DIR"
echo "You can now find File Converter Pro in your application menu."
echo ""
echo "Optional: Install ffmpeg and pandoc for full format support:"
echo "  sudo apt install ffmpeg pandoc"
INSTALL

chmod +x dist/install.sh

echo ""
echo "============================================"
echo "  BUILD COMPLETE!"
echo ""
echo "  Output: dist/"
echo "    file-converter-pro/       (Advanced UI)"
echo "    file-converter-pro-simple/ (Simple UI)"
echo "    install.sh                 (Linux installer)"
echo ""
echo "  To install: cd dist && ./install.sh"
echo ""
echo "  To create a .tar.gz for distribution:"
echo "    cd dist && tar -czf FCP-Linux.tar.gz \\"
echo "      file-converter-pro/ file-converter-pro-simple/ install.sh"
echo "============================================"
