# 🔄 File Converter Pro

A modern, professional desktop application for converting files between PDF, Word (DOCX), Markdown, Images, and Text formats.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- 🎨 **Modern Dark UI** - Professional interface with smooth animations
- 📁 **Drag & Drop** - Simply drag files onto the app
- 🔄 **20+ Conversions** - PDF, Word, Markdown, Images, Text
- ⚡ **Fast Processing** - Efficient conversion engine
- 💻 **Native Desktop App** - No browser needed
- 🔒 **Privacy First** - All processing done locally

## 🚀 Quick Start

### Windows

1. **Double-click `START.bat`** (or run `bats/start.bat`)
2. Wait for first-time setup (installs dependencies)
3. The app opens automatically!

### macOS / Linux

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

## 📁 Project Structure

```
File-Converter/
├── app.py                 # Main application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── START.bat             # Windows launcher
├── .gitignore            # Git ignore rules
├── bats/                 # Batch scripts
│   ├── start.bat         # Main start script
│   ├── start_debug.bat   # Debug mode
│   └── create_shortcut.bat # Desktop shortcut creator
├── backend/              # Conversion engine
│   ├── main.py           # FastAPI backend (optional)
│   └── converters/       # File converters
│       ├── pdf_converter.py
│       ├── word_converter.py
│       ├── markdown_converter.py
│       ├── image_converter.py
│       └── text_converter.py
├── frontend/             # Web UI (optional)
│   ├── index.html
│   ├── css/
│   └── js/
├── uploads/              # Temporary uploads (gitignored)
└── converted/            # Output files (gitignored)
```

## 🔄 Supported Conversions

| From \ To | PDF | DOCX | MD | TXT | PNG | JPG |
|-----------|-----|------|-----|-----|-----|-----|
| **PDF**   |  -  |  ✅  | ✅ | ✅ | ✅ | ✅ |
| **DOCX**  |  ✅  |  -  | ✅ | ✅ | ❌ | ❌ |
| **MD**    |  ✅  |  ✅  | - | ✅ | ❌ | ❌ |
| **TXT**   |  ✅  |  ✅  | ✅ | - | ❌ | ❌ |
| **PNG**   |  ✅  |  ❌  | ❌ | ❌ | - | ✅ |
| **JPG**   |  ✅  |  ❌  | ❌ | ❌ | ✅ | - |

## 🛠️ Development

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
python app.py
```

### Creating Desktop Shortcut (Windows)

Run `bats/create_shortcut.bat` to create a shortcut on your Desktop.

## 📝 Requirements

- Python 3.8+
- Windows 10/11, macOS, or Linux
- See `requirements.txt` for Python packages

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details.

---

Made with ❤️ using Python and CustomTkinter
