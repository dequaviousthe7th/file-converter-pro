# Third-Party Components Bundled with File Converter Pro

File Converter Pro itself is MIT-licensed (see the repository `LICENSE`). The
app additionally bundles the following third-party tools. The GPL-licensed
tools (ffmpeg, pandoc) are shipped as **separate executables** that the app
spawns as subprocesses with command-line arguments — they are never linked
into the application ("mere aggregation"), so their licenses apply to those
binaries only, not to File Converter Pro.

Binaries are not stored in this repository; they are downloaded at build time
by `scripts/fetch-sidecars.sh` / `scripts/fetch-sidecars.ps1` from the sources
below and bundled per-platform by Tauri.

| Component | Version | License | Role | Source |
|---|---|---|---|---|
| FFmpeg (Windows x64) | 8.1.x GPL static build (BtbN `n8.1` branch, rolling `latest` tag) | GPL-3.0 — [`LICENSE.ffmpeg.txt`](LICENSE.ffmpeg.txt) | Audio/video conversion, HEIC decode, video→GIF (sidecar) | [BtbN/FFmpeg-Builds releases](https://github.com/BtbN/FFmpeg-Builds/releases/tag/latest) — asset `ffmpeg-n8.1-latest-win64-gpl-8.1.zip` |
| FFmpeg (Linux x64) | 8.1.x GPL static build (BtbN `n8.1` branch, rolling `latest` tag) | GPL-3.0 — [`LICENSE.ffmpeg.txt`](LICENSE.ffmpeg.txt) | Same as above | [BtbN/FFmpeg-Builds releases](https://github.com/BtbN/FFmpeg-Builds/releases/tag/latest) — asset `ffmpeg-n8.1-latest-linux64-gpl-8.1.tar.xz` |
| FFmpeg (macOS arm64 + x64) | 8.1.x release-channel build (currently 8.1.2) | GPL-3.0 — [`LICENSE.ffmpeg.txt`](LICENSE.ffmpeg.txt) | Same as above | [ffmpeg.martin-riedl.de](https://ffmpeg.martin-riedl.de/) — `redirect/latest/macos/{arm64,amd64}/release/ffmpeg.zip` |
| pandoc | 3.10.1 | GPL-2.0-or-later — [`LICENSE.pandoc.txt`](LICENSE.pandoc.txt) | Document conversion hub: MD/HTML/DOCX/RTF/EPUB/TXT, and →PDF via typst (sidecar) | [jgm/pandoc release 3.10.1](https://github.com/jgm/pandoc/releases/tag/3.10.1) |
| typst | 0.15.1 | Apache-2.0 — [`LICENSE.typst.txt`](LICENSE.typst.txt) | PDF engine for pandoc (`--pdf-engine=typst`); ships with embedded default fonts (sidecar) | [typst/typst release v0.15.1](https://github.com/typst/typst/releases/tag/v0.15.1) |
| PDFium | `chromium/7961` (bblanchon non-V8 build) | Apache-2.0 & BSD-3-Clause — [`LICENSE.pdfium.txt`](LICENSE.pdfium.txt) | PDF text extraction and PDF→image page rendering (dynamic library, loaded at runtime via `pdfium-render`) | [bblanchon/pdfium-binaries release chromium/7961](https://github.com/bblanchon/pdfium-binaries/releases/tag/chromium%2F7961) |

## Corresponding source code

As required by the GPL, the source code corresponding to the bundled GPL
binaries is available from:

- **FFmpeg**: <https://ffmpeg.org/download.html> (source releases) — the exact
  build scripts and configuration for the bundled Windows/Linux binaries are
  published at <https://github.com/BtbN/FFmpeg-Builds>; the macOS build
  scripts and source references are published at
  <https://ffmpeg.martin-riedl.de/> (see the build info page for each build).
- **pandoc**: <https://github.com/jgm/pandoc> (tag `3.10.1`).

Other sources: typst <https://github.com/typst/typst> (tag `v0.15.1`); PDFium
<https://pdfium.googlesource.com/pdfium/> (built via
<https://github.com/bblanchon/pdfium-binaries>).

## License texts in this directory

| File | License | Canonical text source |
|---|---|---|
| `LICENSE.ffmpeg.txt` | GNU GPL v3 | <https://www.gnu.org/licenses/gpl-3.0.txt> |
| `LICENSE.pandoc.txt` | GNU GPL v2 | <https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt> |
| `LICENSE.typst.txt` | Apache License 2.0 | <https://www.apache.org/licenses/LICENSE-2.0.txt> |
| `LICENSE.pdfium.txt` | PDFium license (BSD-3-Clause style, per upstream) | <https://pdfium.googlesource.com/pdfium/+/refs/heads/main/LICENSE> |

Notes:

- The BtbN and martin-riedl FFmpeg builds enable GPLv3 components, so the
  effective license of the bundled ffmpeg binaries is GPL v3.
- pandoc is distributed under "GPL version 2 or later"; the GPL v2 text is
  shipped per the plan's convention.
- The in-process Rust crates used by the conversion engine (image, resvg,
  printpdf, pdfium-render, csv, calamine, rust_xlsxwriter, serde_json,
  serde-saphyr, toml, …) are all MIT/Apache-2.0/BSD/Unlicense; their license
  metadata is tracked via Cargo (`cargo license`) and is not duplicated here.
- Versions above must stay in sync with the `VERSIONS` block at the top of
  `scripts/fetch-sidecars.sh` and `scripts/fetch-sidecars.ps1`.
