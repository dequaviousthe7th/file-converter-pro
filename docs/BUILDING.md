# Building from Source

File Converter Pro is a Tauri 2 app: a Rust conversion engine (`crates/engine`) behind a
thin Tauri shell (`src-tauri`), with a React/TypeScript frontend (`src`). Conversion tools
(ffmpeg, pandoc, typst, pdfium) are fetched by script and bundled as sidecars/resources.

## Prerequisites

All platforms:

- **Rust** (stable) via [rustup](https://rustup.rs)
- **Node.js** 20+ (LTS) with npm

### Windows

- [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
  with the "Desktop development with C++" workload
- [WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)
  (preinstalled on Windows 11 and most Windows 10 machines)

### macOS

- Xcode Command Line Tools: `xcode-select --install`

### Linux / WSL2

```bash
sudo apt update
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev
```

WSL2 counts as Linux (WebKitGTK webview; WSLg displays the window). It's fine for daily
development, but release artifacts are built by CI — don't try to cross-compile Windows or
macOS builds from WSL2.

## Setup

```bash
git clone https://github.com/dequaviousthe7th/File-Converter.git
cd File-Converter
npm install
```

Fetch the sidecar binaries (ffmpeg, pandoc, typst) and the pdfium library for your target
triple:

```bash
# Linux / WSL2
bash scripts/fetch-sidecars.sh x86_64-unknown-linux-gnu

# macOS (Apple Silicon)
bash scripts/fetch-sidecars.sh aarch64-apple-darwin

# macOS (Intel)
bash scripts/fetch-sidecars.sh x86_64-apple-darwin

# Windows (PowerShell)
scripts/fetch-sidecars.ps1 x86_64-pc-windows-msvc
```

This populates `src-tauri/binaries/` (target-triple-suffixed sidecars) and
`src-tauri/resources/pdfium/`. Both are gitignored; exact pinned versions live in the
script's `VERSIONS` block.

## Development

```bash
npm run tauri dev
```

Starts Vite on `http://localhost:1420` and launches the app with hot reload.

## Release build

```bash
npm run tauri build
```

Bundles land in `src-tauri/target/release/bundle/` (NSIS `-setup.exe` on Windows, `.dmg` on
macOS, `.AppImage` + `.deb` on Linux). Official releases are built and signed by
`.github/workflows/release.yml` — see [RELEASING.md](RELEASING.md) and
[SIGNING.md](SIGNING.md).

## Engine tests

The conversion engine is a pure Rust crate with no Tauri/GTK dependencies, so its tests run
anywhere (including WSL2 without webkit2gtk):

```bash
cargo test -p fcp-engine
```

Sidecar-dependent tests (audio/video, pandoc documents, pdfium rendering) are gated: they
run only when the tool is found on `PATH` or pointed to explicitly, and skip silently
otherwise.

```bash
# Run the gated tests too
sudo apt install ffmpeg pandoc          # or:
FCP_FFMPEG=/path/to/ffmpeg FCP_PANDOC=/path/to/pandoc \
FCP_TYPST=/path/to/typst FCP_PDFIUM=/path/to/libpdfium.so \
cargo test -p fcp-engine
```

Lints match CI:

```bash
cargo fmt --check
cargo clippy -p fcp-engine -- -D warnings
```

## Project layout

```
/                     # cargo workspace root
  src/                # React frontend (Vite + Tailwind v4)
    components/       # titlebar, drop zone, file rows, ...
    views/            # Convert / History / Settings
    lib/              # types, IPC wrappers, zustand store
  src-tauri/          # Tauri shell: commands, job registry, settings, history
    binaries/         # sidecars, target-triple suffixed (gitignored; fetched by script)
    resources/        # pdfium per-OS (gitignored; fetched by script)
  crates/engine/      # fcp-engine: all conversion logic, pure Rust, testable without GTK
  scripts/            # fetch-sidecars.(sh|ps1)
  .github/workflows/  # ci.yml (test/lint), release.yml (tauri-action + signing)
  docs/               # BUILDING.md, SIGNING.md, RELEASING.md
  licenses/           # ffmpeg/pandoc/typst/pdfium license texts + source links
  assets/             # logo + screenshots
```
