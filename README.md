# 🔄 File Converter Pro

A modern, professional desktop application for converting files between PDF, Word (DOCX), Markdown, Images, and Text formats. Built with Python and Tkinter.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/badge/version-1.1.0-brightgreen.svg)

## ✨ Features

- 🎨 **Dual UI Modes** - Choose between Simple (WinRAR-style) or Advanced (Modern Dark) interface
- 📁 **Drag & Drop** - Simply drag files onto the app (Advanced UI)
- 🔄 **20+ Conversions** - PDF, Word, Markdown, Images, Text, HTML
- ⚡ **Instant Kill** - Stop conversions immediately with one click
- 📊 **Progress Tracking** - Visual progress bar with smooth animations
- 💻 **Native Desktop App** - No browser needed
- 🔒 **Privacy First** - All processing done locally

## 🖼️ Screenshots

### Simple UI (WinRAR Style)
<!-- Add screenshot here: ![Simple UI](screenshots/simple_ui.png) -->
```
[SIMPLE UI SCREENSHOT PLACEHOLDER]
```

### Advanced UI (Modern Dark Theme)
<!-- Add screenshot here: ![Advanced UI](screenshots/advanced_ui.png) -->
```
[ADVANCED UI SCREENSHOT PLACEHOLDER]
```

## 🚀 Quick Start

### Windows

Choose your preferred interface:

**Simple UI (Classic Style):**
1. Double-click `START_SIMPLE.bat`
2. Select a file using the Browse button
3. Choose output format from the radio buttons
4. Click "Convert File"

**Advanced UI (Modern Dark):**
1. Double-click `START.bat`
2. Drag & drop files or click the sidebar button
3. Select output format from the grid
4. Click "Start Conversion"

### macOS / Linux

```bash
# Install dependencies
pip install -r requirements.txt

# Run Simple UI
python app_simple.py

# Run Advanced UI
python app.py
```

## 📋 Interface Comparison

| Feature | Simple UI | Advanced UI |
|---------|-----------|-------------|
| **Style** | WinRAR Classic | Modern Dark |
| **Framework** | Standard Tkinter | CustomTkinter |
| **Drag & Drop** | ❌ | ✅ |
| **Kill Button** | ☠️ Instant Kill | ⏹ Stop |
| **Window Size** | Fixed 400x500px | Resizable |
| **Best For** | Quick conversions | Batch operations |

## 🔄 Supported Conversions

| From \ To | PDF | DOCX | MD | TXT | PNG | JPG | WEBP | BMP | HTML |
|-----------|-----|------|-----|-----|-----|-----|------|-----|------|
| **PDF**   |  -  |  ✅  | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **DOCX**  |  ✅  |  -  | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **MD**    |  ✅  |  ✅  | - | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **TXT**   |  ✅  |  ✅  | ✅ | - | ❌ | ❌ | ❌ | ❌ | ❌ |
| **PNG**   |  ✅  |  ❌  | ❌ | ❌ | - | ✅ | ✅ | ✅ | ❌ |
| **JPG**   |  ✅  |  ❌  | ❌ | ❌ | ✅ | - | ✅ | ✅ | ❌ |
| **WEBP**  |  ✅  |  ❌  | ❌ | ❌ | ✅ | ✅ | - | ✅ | ❌ |
| **BMP**   |  ✅  |  ❌  | ❌ | ❌ | ✅ | ✅ | ✅ | - | ❌ |
| **HTML**  |  ✅  |  ❌  | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | - |

## 🛠️ Development

### Project Structure

```
File-Converter/
├── app.py                 # Advanced UI (Modern Dark)
├── app_simple.py          # Simple UI (WinRAR Style)
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── START.bat             # Windows launcher (Advanced)
├── START_SIMPLE.bat      # Windows launcher (Simple)
├── .gitignore            # Git ignore rules
├── backend/              # Conversion engine
│   ├── main.py           # FastAPI backend (optional)
│   └── converters/       # File converters
│       ├── pdf_converter.py
│       ├── word_converter.py
│       ├── markdown_converter.py
│       ├── image_converter.py
│       └── text_converter.py
├── converted/            # Output files (gitignored)
└── coverage/             # Test coverage reports
```

### Setup

```bash
# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python app_simple.py        # Simple UI
python app.py               # Advanced UI
```

## 📝 Requirements

- Python 3.8+
- Windows 10/11, macOS, or Linux
- Microsoft Word (for PDF→DOCX on Windows)
- See `requirements.txt` for Python packages

### Key Dependencies

- `customtkinter` - Modern UI components
- `pdf2docx` - PDF to Word conversion
- `pypdf` - PDF text extraction
- `reportlab` - PDF generation
- `Pillow` - Image processing
- `python-docx` - Word document handling

## 🐛 Known Limitations

- **PDF→DOCX on Windows**: Requires Microsoft Word to be installed
- **DOCX→PDF**: Uses docx2pdf library (Windows) or LibreOffice fallback
- **PDF→Image**: First page only, requires poppler on some systems

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details.

---

Made with ❤️ by Dequavious | Version 1.1.0
