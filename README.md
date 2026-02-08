# File Converter Pro

A powerful desktop file converter with dual UI modes. Convert between documents, images, audio, video, spreadsheets, and config formats. All processing done locally.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/badge/version-2.0.0-brightgreen.svg)

## Features

- **Dual UI Modes** - Simple (WinRAR-style classic) or Advanced (dark sleek modern)
- **200+ Conversion Paths** - Documents, images, audio, video, spreadsheets, config files
- **Batch Conversion** - Convert multiple files at once in both UIs
- **Drag & Drop** - Drop files directly onto the app window
- **Kill Button** - Instantly cancel any conversion in both UIs
- **Real Progress** - Actual conversion progress with status messages
- **Conversion History** - Track past conversions (Advanced UI)
- **Settings** - Configure output folder, quality, bitrate
- **Cross-Platform** - Windows, macOS, and Linux support
- **Privacy First** - All processing done locally, no uploads

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

### Data/Spreadsheets
| From | To |
|------|----|
| CSV, XLSX, JSON, TSV | CSV, XLSX, JSON, TSV, HTML |

### Config
| From | To |
|------|----|
| JSON | YAML, TOML |
| YAML | JSON, TOML |
| TOML | JSON, YAML |

## Quick Start

### Windows

**Simple UI:** Double-click `START_SIMPLE.bat`

**Advanced UI:** Double-click `START.bat`

### macOS / Linux

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Simple UI
python app_simple.py

# Run Advanced UI
python app.py
```

### System Dependencies

Some conversions need system tools installed:

| Tool | Needed For | Install |
|------|-----------|---------|
| **ffmpeg** | Audio & video conversion | [ffmpeg.org/download](https://ffmpeg.org/download.html) |
| **LibreOffice** | DOCX to PDF fallback | [libreoffice.org](https://www.libreoffice.org/) |
| **Pandoc** | Document conversion fallback | [pandoc.org](https://pandoc.org/) |

## UI Comparison

| Feature | Simple UI | Advanced UI |
|---------|-----------|-------------|
| **Style** | WinRAR Classic | Dark Sleek (Discord/Spotify) |
| **Framework** | Standard Tkinter | CustomTkinter |
| **Drag & Drop** | Whole-window overlay | Whole-window overlay |
| **Kill Button** | Yes | Yes |
| **Batch Mode** | Checkbox toggle | Dedicated page |
| **History** | - | Full history tracking |
| **Settings** | - | Output folder, quality, bitrate |
| **Best For** | Quick single conversions | Power users, batch work |

## Project Structure

```
File-Converter/
├── app.py                     # Advanced UI (Dark Sleek Theme)
├── app_simple.py              # Simple UI (WinRAR Style)
├── config.py                  # Centralized config & format registry
├── requirements.txt           # Python dependencies
├── START.bat                  # Windows launcher (Advanced)
├── START_SIMPLE.bat           # Windows launcher (Simple)
├── backend/
│   ├── converter_registry.py  # Maps extensions to converters
│   ├── batch_converter.py     # Batch conversion engine
│   ├── history.py             # Conversion history tracking
│   ├── settings.py            # Persistent settings
│   └── converters/
│       ├── base_converter.py  # Base class (cancel/progress)
│       ├── pdf_converter.py   # PDF conversions
│       ├── word_converter.py  # DOCX conversions
│       ├── markdown_converter.py
│       ├── image_converter.py # PNG, JPG, WEBP, TIFF, ICO, SVG, HEIC, GIF
│       ├── text_converter.py  # Plain text conversions
│       ├── audio_converter.py # MP3, WAV, FLAC, OGG, AAC, M4A, WMA
│       ├── video_converter.py # MP4, AVI, MKV, MOV, WebM, GIF
│       ├── data_converter.py  # CSV, XLSX, JSON, TSV
│       ├── code_converter.py  # JSON, YAML, TOML
│       ├── html_converter.py  # HTML conversions
│       └── ebook_converter.py # EPUB, RTF
├── utils/
│   ├── platform_utils.py      # Cross-platform helpers
│   └── file_utils.py          # File validation & temp management
├── converted/                 # Output directory
└── bats/                      # Additional Windows utilities
```

## Key Dependencies

| Package | Purpose |
|---------|---------|
| customtkinter | Modern dark UI framework |
| Pillow | Image processing |
| pdf2docx | PDF to Word |
| pypdf | PDF text extraction |
| reportlab | PDF generation |
| python-docx | Word document handling |
| pydub | Audio conversion (ffmpeg wrapper) |
| pandas + openpyxl | Spreadsheet conversion |
| pyyaml + toml | Config format conversion |
| cairosvg | SVG rasterization |
| pillow-heif | HEIC/HEIF support |
| ebooklib | EPUB reading |
| beautifulsoup4 | HTML parsing |
| tkinterdnd2 | Native drag & drop |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details.

---

**Built by Dequavious | Version 2.0.0**
