<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/CustomTkinter-1c1c24?style=for-the-badge&logo=python&logoColor=00d4aa" alt="CustomTkinter"/>
  <img src="https://img.shields.io/badge/Tkinter-f0f0f0?style=for-the-badge&logo=python&logoColor=333333" alt="Tkinter"/>
  <img src="https://img.shields.io/badge/FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg"/>
  <img src="https://img.shields.io/badge/Pillow-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Pillow"/>
</p>

<h1 align="center">File Converter Pro</h1>

<p align="center">
  <b>Convert anything. Fast. Private. No uploads, no cloud, no limits.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-2.0.0-00d4aa.svg" alt="Version 2.0.0"/>
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"/>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Platform"/>
  <img src="https://img.shields.io/badge/Formats-55+-00d4aa.svg" alt="55+ Formats"/>
</p>

---

## Overview

**File Converter Pro** is a desktop file conversion tool with 200+ conversion paths across documents, images, audio, video, spreadsheets, and config files. Everything runs locally on your machine — no files are uploaded anywhere.

Ships with two UI modes:

| | Simple UI | Advanced UI |
|--|-----------|-------------|
| **Style** | Classic, lightweight | Modern dark studio theme |
| **Framework** | Standard Tkinter | CustomTkinter |
| **Best For** | Quick single conversions | Power users, batch workflows |
| **Batch Mode** | Checkbox toggle | Dedicated page |
| **History** | - | Full conversion history |
| **Settings** | - | Output folder, quality, bitrate |
| **Drag & Drop** | Yes | Yes |
| **Kill Button** | Yes | Yes |

---

## Supported Formats

### Documents

| From | To |
|------|----|
| PDF | DOCX, TXT, MD, PNG, JPG, HTML |
| DOCX | PDF, TXT, MD, HTML |
| TXT | PDF, DOCX, MD |
| Markdown | PDF, DOCX, TXT, HTML |
| HTML | PDF, DOCX, TXT, MD |
| RTF | PDF, DOCX, TXT |
| EPUB | PDF, TXT |

### Images

| From | To |
|------|----|
| PNG, JPG, JPEG | JPG/PNG, WEBP, BMP, PDF, TIFF, ICO, GIF |
| WEBP, BMP, TIFF | PNG, JPG, WEBP, BMP, PDF, TIFF, GIF |
| GIF | PNG, JPG, WEBP, BMP, PDF |
| ICO | PNG, JPG, BMP |
| SVG | PNG, JPG, WEBP, PDF |
| HEIC/HEIF | PNG, JPG, WEBP, BMP, PDF, TIFF |

### Audio (requires ffmpeg)

| From | To |
|------|----|
| MP3, WAV, FLAC, OGG, AAC, M4A, WMA | MP3, WAV, FLAC, OGG, AAC, M4A, WMA |

### Video (requires ffmpeg)

| From | To |
|------|----|
| MP4, AVI, MKV, MOV, WebM | MP4, AVI, MKV, MOV, WebM, GIF |

### Data / Spreadsheets

| From | To |
|------|----|
| CSV | XLSX, JSON, TSV, HTML |
| XLSX | CSV, JSON, TSV, HTML |
| JSON | CSV, XLSX, YAML, TOML, TSV |
| TSV | CSV, XLSX, JSON |

### Config

| From | To |
|------|----|
| YAML | JSON, TOML |
| TOML | JSON, YAML |

---

## Quick Start

### Windows

**Advanced UI** — double-click `START.bat`

**Simple UI** — double-click `START_SIMPLE.bat`

### macOS / Linux

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate app logo (one-time)
python assets/generate_logo.py

# Run Advanced UI
python app.py

# Run Simple UI
python app_simple.py
```

### System Dependencies

Some conversions require external tools:

| Tool | Required For | Install |
|------|-------------|---------|
| **ffmpeg** | Audio & video conversion | [ffmpeg.org/download](https://ffmpeg.org/download.html) |
| **Pandoc** | Document conversion fallback | [pandoc.org](https://pandoc.org/) |

---

## Features

- **200+ Conversion Paths** across 55+ file formats
- **Dual UI Modes** — Classic simple or modern dark theme
- **Batch Conversion** — Convert multiple files in a single queue
- **Drag & Drop** — Drop files directly onto the window
- **Kill Button** — Cancel any conversion instantly
- **Real Progress** — Live progress reporting with status messages
- **Conversion History** — Track all past conversions (Advanced UI)
- **Configurable Settings** — Output folder, image quality, audio bitrate
- **Cross-Platform** — Windows, macOS, and Linux
- **100% Local** — No internet required, no files uploaded

---

## Project Structure

```
File-Converter/
├── app.py                     # Advanced UI
├── app_simple.py              # Simple UI
├── config.py                  # Format registry & app config
├── requirements.txt           # Python dependencies
├── START.bat                  # Windows launcher (Advanced)
├── START_SIMPLE.bat           # Windows launcher (Simple)
├── assets/
│   ├── generate_logo.py       # Logo generator script
│   ├── logo.ico               # App icon (generated)
│   └── logo.png               # Logo image (generated)
├── backend/
│   ├── converter_registry.py  # Extension -> converter mapping
│   ├── batch_converter.py     # Batch conversion engine
│   ├── history.py             # Conversion history
│   ├── settings.py            # Persistent settings
│   └── converters/
│       ├── base_converter.py  # Base class with cancel/progress
│       ├── pdf_converter.py
│       ├── word_converter.py
│       ├── markdown_converter.py
│       ├── image_converter.py # PNG, JPG, WEBP, TIFF, ICO, SVG, HEIC, GIF
│       ├── text_converter.py
│       ├── audio_converter.py # MP3, WAV, FLAC, OGG, AAC, M4A, WMA
│       ├── video_converter.py # MP4, AVI, MKV, MOV, WebM, GIF
│       ├── data_converter.py  # CSV, XLSX, JSON, TSV
│       ├── code_converter.py  # JSON, YAML, TOML
│       ├── html_converter.py
│       └── ebook_converter.py # EPUB, RTF
├── utils/
│   ├── platform_utils.py      # Cross-platform helpers
│   └── file_utils.py          # File validation & temp files
├── converted/                 # Default output directory
└── bats/                      # Windows utility scripts
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| **customtkinter** | Modern dark UI framework (Advanced UI) |
| **Pillow** | Image processing & conversion |
| **pdf2docx** | PDF to Word conversion |
| **pypdf** | PDF reading & text extraction |
| **reportlab** | PDF generation |
| **python-docx** | Word document handling |
| **pydub** | Audio conversion (ffmpeg wrapper) |
| **ffmpeg-python** | Video conversion (ffmpeg wrapper) |
| **pandas** | Data format conversion |
| **openpyxl** | Excel file handling |
| **pyyaml** | YAML support |
| **toml** | TOML support |
| **cairosvg** | SVG rasterization |
| **pillow-heif** | HEIC/HEIF image support |
| **ebooklib** | EPUB reading |
| **beautifulsoup4** | HTML parsing |
| **tkinterdnd2** | Native drag & drop |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <b>Built by <a href="https://github.com/dequaviousthe7th">Dequavious</a></b>
</p>
