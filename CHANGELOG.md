# Changelog

All notable changes to File Converter Pro are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-07-25

Complete rewrite. The Python/tkinter implementation is replaced by a Tauri 2 app: a pure
Rust conversion engine behind a thin shell, with a single premium React UI.

### Added

- Fully standalone: ffmpeg, pandoc, and typst are bundled as sidecars, pdfium as a
  resource — no external tool installs, no winget prompts, works on a bare machine
- Signed releases: Windows installers via SignPath Foundation, macOS builds signed and
  notarized with an Apple Developer ID, GPG-signed `SHA256SUMS` on Linux
- Real PDF → PNG/JPG: pages are actually rendered (all pages, configurable DPI)
- EPUB → DOCX conversion path
- Per-file target pickers in the batch queue, with "apply to all compatible"
- After-conversion behavior setting (ask / open folder / notify)
- PDF render DPI setting
- One-time import of v2 settings and history on first run
- macOS (Apple Silicon + Intel) and Linux (AppImage + .deb) release artifacts
- Auto-update-ready infrastructure (Tauri updater wiring)

### Changed

- New stack: Tauri 2 shell + Rust engine (`fcp-engine`) + React/TypeScript frontend
- Windows installer is now NSIS, per-user, no admin rights (replaces Inno Setup);
  v2 users must uninstall v2 once — see the README migration note
- Default output directory is now `~/Documents/File Converter Pro` instead of the
  install directory; outputs are uniquely named on collision (`_converted`, ` (1)`, …)

### Fixed

- Silent output overwrites — conversions now never clobber existing files
- Orphaned ffmpeg processes after cancel or app exit — children are killed and partial
  outputs cleaned up
- Dead settings controls — image quality, audio bitrate, and output folder are now
  actually applied to conversions
- Batch queue re-converting already-completed items on re-run
- Fake PDF → image output (was a rendered text preview; now real page rendering)
- Batch and Simple-UI conversions missing from history — every conversion is recorded

### Removed

- Dual Advanced/Simple UI — one interface now
- Python implementation (`app.py`, `app_simple.py`, `backend/`, `utils/`, Inno Setup
  installer)
- Optional ffmpeg/pandoc download steps in the installer (everything is bundled)

## [2.0.0] and earlier

Python/tkinter releases (dual Advanced/Simple UI, Inno Setup installer). Predates this
changelog; see the git history.

[3.0.0]: https://github.com/dequaviousthe7th/File-Converter/releases/tag/v3.0.0
