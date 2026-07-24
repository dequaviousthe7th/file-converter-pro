<p align="center">
  <img src="assets/logo.png" alt="File Converter Pro" width="120"/>
</p>

<h1 align="center">File Converter Pro</h1>

<p align="center">
  <b>Convert anything. Fast. Private. No uploads, no cloud, no limits.</b>
</p>

<p align="center">
  <a href="https://github.com/dequaviousthe7th/File-Converter/releases/latest"><img src="https://img.shields.io/badge/Download-Latest%20Release-00d4aa?style=for-the-badge&logo=github&logoColor=white" alt="Download"/></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-3.0.0-00d4aa.svg" alt="Version 3.0.0"/>
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"/>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Platform"/>
  <img src="https://img.shields.io/badge/Conversion%20Paths-158-00d4aa.svg" alt="158 Conversion Paths"/>
</p>

---

## Download

Grab the latest release from the **[Releases](https://github.com/dequaviousthe7th/File-Converter/releases/latest)** page:

| OS | Download | Notes |
|----|----------|-------|
| **Windows** (10/11, x64) | the `…-setup.exe` installer | Per-user install — no admin rights needed |
| **macOS** (Apple Silicon) | the `…_aarch64.dmg` | Signed & notarized by Apple |
| **macOS** (Intel) | the `…_x64.dmg` | Signed & notarized by Apple |
| **Linux** | the `.AppImage` | Portable — `chmod +x` and run |
| **Linux** (Debian/Ubuntu) | the `.deb` | `sudo dpkg -i` to install |

Each release lists the exact file names on its Releases page. Everything is bundled — no
separate ffmpeg or Pandoc installs, ever.

## Trusted & secure

- **Code-signed releases.** Windows installers are signed through [SignPath Foundation](https://signpath.org)'s free open-source signing program; macOS builds are signed with an Apple Developer ID and notarized by Apple. See [docs/SIGNING.md](docs/SIGNING.md) for the full signing setup.
- **Checksums on every release.** Each release ships a `SHA256SUMS` file. Verify with `sha256sum -c SHA256SUMS` (Linux/macOS) or `certutil -hashfile <file> SHA256` (Windows).
- **100% local processing.** Files never leave your machine. No uploads, no telemetry, no analytics, no network calls during conversion.

## Overview

File Converter Pro is a standalone desktop app that converts documents, images, audio, video, spreadsheets, and config files — **158 conversion paths**, all processed locally. Version 3 is a ground-up rebuild: a Rust conversion engine inside a Tauri 2 shell, with a single premium dark UI (the old Advanced/Simple split is gone).

<!-- SCREENSHOT: convert view -->

<!-- SCREENSHOT: history view -->

<!-- SCREENSHOT: settings view -->

## Supported formats

### Documents

| From | To |
|------|----|
| PDF | DOCX, TXT, MD, PNG, JPG, HTML |
| DOCX | PDF, TXT, MD, HTML |
| MD | PDF, DOCX, TXT, HTML |
| TXT | PDF, DOCX, MD |
| HTML | PDF, DOCX, TXT, MD |
| RTF | PDF, DOCX, TXT |
| EPUB | PDF, TXT, DOCX |

> PDF → PNG/JPG renders the actual pages (every page, at your configured DPI) — no more text-preview stand-ins. PDF → DOCX/TXT/MD extracts text content; complex layouts are not preserved (true of every non-Acrobat tool).

### Images

| From | To |
|------|----|
| PNG | JPG, WEBP, BMP, PDF, TIFF, ICO, GIF |
| JPG | PNG, WEBP, BMP, PDF, TIFF, ICO, GIF |
| WEBP | PNG, JPG, BMP, PDF, TIFF, GIF |
| BMP | PNG, JPG, WEBP, PDF, TIFF, GIF |
| TIFF | PNG, JPG, WEBP, BMP, PDF, GIF |
| GIF | PNG, JPG, WEBP, BMP, PDF |
| ICO | PNG, JPG, BMP |
| SVG | PNG, JPG, WEBP, PDF |
| HEIC | PNG, JPG, WEBP, BMP, PDF, TIFF |

> `jpeg`, `tif`, `yml`, `heif`, and `htm` files are accepted as inputs and treated as their canonical formats.

### Audio

| From | To |
|------|----|
| MP3 | WAV, FLAC, OGG, AAC, M4A, WMA |
| WAV | MP3, FLAC, OGG, AAC, M4A |
| FLAC | MP3, WAV, OGG, AAC, M4A |
| OGG | MP3, WAV, FLAC, AAC, M4A |
| AAC | MP3, WAV, FLAC, OGG, M4A |
| M4A | MP3, WAV, FLAC, OGG, AAC |
| WMA | MP3, WAV, FLAC, OGG, M4A |

### Video

| From | To |
|------|----|
| MP4 | AVI, MKV, MOV, WEBM, GIF |
| AVI | MP4, MKV, MOV, WEBM, GIF |
| MKV | MP4, AVI, MOV, WEBM, GIF |
| MOV | MP4, AVI, MKV, WEBM, GIF |
| WEBM | MP4, AVI, MKV, MOV, GIF |

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

## Features

- **Batch queue with per-file targets** — drop a mixed pile of files, pick a target per file (or apply to all compatible), convert the lot
- **Real progress** — live per-file progress bars with status messages, including ffmpeg time-based progress for audio/video
- **Cancel anytime** — per-file or all at once; no orphaned processes, partial outputs are cleaned up
- **Conversion history** — every conversion recorded (single and batch), with open / show-in-folder actions
- **Configurable** — output folder, after-conversion behavior, image quality, audio bitrate, PDF render DPI — all settings actually applied
- **Drag & drop** — drop files straight onto the window
- **Never overwrites** — outputs are uniquely named (`_converted`, then ` (1)`, ` (2)`, …)
- **Dark premium UI** — custom titlebar, smooth motion, one focused workflow
- **Auto-update ready** — updater infrastructure is wired for signed in-app updates
- **100% local** — no internet required, no files uploaded anywhere

## Building from source

```bash
git clone https://github.com/dequaviousthe7th/File-Converter.git
cd File-Converter
npm install
bash scripts/fetch-sidecars.sh <your-target-triple>   # e.g. x86_64-unknown-linux-gnu
npm run tauri dev
```

Full prerequisites (per OS), release builds, and engine tests: **[docs/BUILDING.md](docs/BUILDING.md)**.

## Upgrading from v2

Version 3 is a new engine with a new installer. If you have File Converter Pro 2.x installed:

1. Uninstall v2 once via *Add/Remove Programs* (the old installer can't upgrade in place).
2. Install v3. Your v2 settings and conversion history are automatically imported on first run.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.

File Converter Pro bundles third-party tools that run as separate processes: **ffmpeg** (GPL), **pandoc** (GPL), **typst** (Apache-2.0), and the **pdfium** library. Their license texts, exact versions, and source links are in [licenses/README.md](licenses/README.md).

---

<p align="center">
  <b>Built by <a href="https://github.com/dequaviousthe7th">Dequavious</a></b>
</p>
