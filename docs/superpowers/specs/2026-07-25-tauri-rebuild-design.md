# File Converter Pro 3.0 — Tauri Rebuild Design

Date: 2026-07-25
Status: approved for implementation (mandate: full rebuild, premium single UI, standalone, signed releases)

## 1. Goal

Replace the Python/tkinter implementation with a native-quality, cross-platform desktop app:

- One beautiful, premium UI (the Advanced/Simple split is retired).
- Standalone: bundles every conversion engine it needs — no winget/ffmpeg/pandoc install steps.
- Small, fast, professional: Tauri 2 shell, Rust conversion engine.
- Signed, trusted releases from GitHub: no SmartScreen/Gatekeeper scare screens once the
  signing programs (SignPath Foundation, Apple Developer) are enrolled.
- Full feature parity with v2 (178 conversion pairs) minus its bugs, plus real settings.

## 2. Stack (verified current, July 2026)

| Layer | Choice | Version |
|---|---|---|
| Shell | Tauri | 2.x (core 2.11.x) |
| Frontend | React + TypeScript + Vite | React 19, Vite 7 |
| Styling | Tailwind CSS v4 + shadcn/ui primitives + motion | — |
| Engine | Rust workspace crate `fcp-engine` (no Tauri dependency) | Rust 2021 |
| Sidecars | ffmpeg ≥8.1 (GPL static), pandoc 3.10.x, typst 0.15.x | per-OS |
| PDF lib | pdfium (bblanchon non-V8) loaded at runtime via `pdfium-render` | chromium/79xx |

Rationale: Tauri beats Electron/Flutter/Qt on download size (5–10 MB shell), native webviews,
Rust backend, official CI/updater tooling. React+shadcn is the Spacedrive stack — best
component ecosystem for a solo dev to reach premium polish.

## 3. Repository layout

```
/                     # cargo workspace root
  src/                # React frontend (Vite)
  src-tauri/          # Tauri app crate (thin shell: commands, jobs, events)
    binaries/         # sidecars, target-triple suffixed (gitignored; fetched by script)
    resources/        # pdfium per-OS (gitignored; fetched by script)
  crates/engine/      # fcp-engine: all conversion logic, pure Rust, testable without GTK
  scripts/            # fetch-sidecars.(sh|ps1), icon generation
  .github/workflows/  # ci.yml (test/lint), release.yml (tauri-action + signing)
  docs/               # BUILDING.md, SIGNING.md, RELEASING.md
  licenses/           # ffmpeg/pandoc/typst/pdfium license texts + source links
  assets/             # logo, icons (kept from v2)
```

The engine crate has zero Tauri/GTK dependencies so `cargo test -p fcp-engine` runs anywhere
(including WSL2 without webkit2gtk). The Tauri crate is a thin adapter.

## 4. Conversion engine

### 4.1 Format registry
Single source of truth in `fcp-engine::registry` (Rust), exported to the frontend via a
`formats()` command. Reproduces v2's `config.py` matrix verbatim (178 pairs, aliases
jpeg/tif/yml normalized), with these deliberate changes:
- `htm` fully registered as an HTML input alias (was half-registered).
- `epub → docx` exposed (pandoc does it natively; engine already supported it hidden).
- `pdf → png/jpg` becomes REAL (pdfium page rendering, all pages, `{stem}_page{N}` naming)
  instead of v2's fake text-preview image.
- No `→ heic` output (unchanged from v2; HEIC is input-only).

### 4.2 Domain implementations

| Domain | Engine | Notes |
|---|---|---|
| Raster images | `image` 0.25 + `fast_image_resize` + `webp` (lossy) + `ico-builder` | JPEG q from settings + optimize, TIFF LZW, ICO multi-size (16–256), alpha→white for jpg/bmp, EXIF orientation applied |
| SVG | `resvg` (raster), `svg2pdf` (vector PDF) | bundled fallback font for text |
| HEIC/HEIF | ffmpeg sidecar decode → PNG intermediate → image crate | requires ffmpeg ≥8.1 (tiled HEIF); no libheif |
| Animated GIF, video→GIF | ffmpeg two-pass palettegen/paletteuse, fps=10 scale=480 lanczos (v2 parity) | |
| Image→PDF | `printpdf` (pinned), JPEG DCT pass-through | |
| Audio | ffmpeg sidecar; container map: aac=adts, m4a=ipod, wma=asf/wmav2, ogg=vorbis | bitrate from settings (128k–320k), metadata `-map_metadata 0` |
| Video | ffmpeg sidecar; mp4/mov=x264+aac+faststart, avi=x264+mp3, mkv=x264+aac, webm=vp9+opus 2M | progress via `-progress pipe:1`; cancel kills child |
| Documents (md/html/docx/rtf/epub/txt ↔) | pandoc sidecar | reference styling; best-in-class fidelity |
| X→PDF | pandoc `--pdf-engine=<bundled typst>` | typst embeds fonts; no LaTeX |
| PDF→txt/md | pdfium text extraction (fallback `pdf-extract`) | labeled "text extraction" in UI |
| PDF→docx | pdfium text → markdown → pandoc | labeled: layout not preserved |
| PDF→png/jpg | pdfium render at 144 DPI (configurable) | all pages |
| CSV/TSV/XLSX/JSON | `csv`, `calamine` (read), `rust_xlsxwriter` (write), `serde_json` preserve_order | HTML table output kept (styled page) |
| JSON/YAML/TOML | `serde-saphyr` + `toml` via a single `serde_json::Value` hub | explicit errors: TOML null/root/datetime; YAML 1.2 scalars |

### 4.3 Jobs, progress, cancellation
- `JobId`-keyed registry in Tauri state. Each conversion runs on a blocking task with a
  `CancellationToken`; progress streams to the frontend over a `tauri::ipc::Channel`
  (`{ jobId, pct, message, state }`).
- Sidecar processes are registered with the job; cancel = token + `Child::kill()` + partial
  output cleanup. App exit kills all children. No orphaned ffmpeg (v2 bug fixed).
- Batch = sequential queue over the same machinery; per-item statuses
  pending/converting/done/failed/cancelled; re-running a queue skips done items (v2 bug fixed).

### 4.4 Output
- Naming: `{stem}_converted.{ext}` (v2 contract), with ` (1)`, ` (2)` unique-suffixing on
  collision — never silently overwrite (v2 bug fixed).
- Default output dir: `~/Documents/File Converter Pro` (user-writable; v2 wrote inside the
  install dir). Configurable, restored at startup (v2 bug fixed).

## 5. UI (single, premium)

Dark studio theme, brand continuity: charcoal `#111116` base, teal `#00d4aa` accent,
existing swap-arrow logo. Custom titlebar (`decorations:false`, drag region, min/max/close).
Three views (left rail or top nav — decided during frontend build):

1. **Convert** — unified single+batch surface. Hero drop-zone (OS drag-and-drop via
   `onDragDropEvent`); dropped/browsed files become queue rows (icon, name, size, per-file
   target picker with smart default + "apply to all compatible"); per-row progress bars,
   Convert All / Cancel; success row actions: Open File / Show in Folder. This replaces both
   v2 UIs and fixes the union-target-menu design flaw.
2. **History** — all conversions recorded (single AND batch, both fixed from v2): source,
   output, status, time, duration; open/reveal actions; clear. Schema matches v2
   (`~/.file-converter-pro/history.json` equivalent in app-data dir, 200-record cap).
3. **Settings** — all wired for real this time: output folder, after-conversion behavior
   (ask / open folder / notify), image quality (10–100, drives JPEG/WebP encode), audio
   bitrate (128k/192k/256k/320k, drives ffmpeg), PDF render DPI. Persisted with
   tauri-plugin-store.

Empty states, toasts (banner parity), keyboard/reduced-motion respect, format-count footer.

## 6. Distribution, signing, trust

### 6.1 Artifacts (GitHub Releases via tauri-action)
- Windows: NSIS `File-Converter-Pro_3.0.0_x64-setup.exe` (per-user, no UAC).
- macOS: signed+notarized `.dmg` for aarch64 + x86_64.
- Linux: AppImage + .deb (built on ubuntu-22.04) + SHA256SUMS.

### 6.2 Signing plan (2026 reality)
- EV certs no longer buy SmartScreen reputation (Microsoft removed EV OIDs Aug 2024) — not worth $300+/yr.
- **Windows primary: SignPath Foundation** — free for OSS (this repo is MIT ✓), publisher
  shows "SignPath Foundation" whose shared reputation clears SmartScreen from release one.
  Requires: published signing policy page, MFA, CI-built releases, per-release approval click.
  CI integration: two-stage (sign app exe → bundle NSIS → sign installer) via
  `signpath/github-action-submit-signing-request`, activated when SignPath secrets exist.
- Windows fallbacks: Certum Open Source (~$55/yr, any country, reputation ramps) or Azure
  Artifact Signing ($9.99/mo; individuals US/CA only as of 07/2026).
- **macOS: Apple Developer Program ($99/yr) — non-negotiable.** Sequoia/Tahoe removed
  right-click-open; unsigned apps are effectively dead for non-technical users. CI signs +
  notarizes automatically when `APPLE_*` secrets exist.
- Linux: GPG-signed SHA256SUMS.
- CI is built so unsigned builds still work (secrets absent → signing steps skip) — the app
  ships first, signing activates the moment enrollment completes.

### 6.3 Sidecar licensing
ffmpeg (GPL build) and pandoc (GPL-2.0+) run as spawned subprocesses = mere aggregation; app
stays MIT. Ship `licenses/` with texts, exact versions, and source links; surfaced in About.

## 7. Testing
- Engine: unit tests per domain with generated fixtures; value-hub round-trip property tests;
  unique-naming tests; sidecar tests skip gracefully when binary absent.
- CI (`ci.yml`): fmt + clippy + `cargo test -p fcp-engine` + `tsc` + vite build on
  ubuntu/windows/macos.
- Release dry-run workflow_dispatch before first tag.

## 8. Migration / cleanup
- Python implementation (app.py, app_simple.py, backend/, utils/, config.py, requirements.txt,
  START*.bat, installer/) is removed once the new app builds; git history preserves it.
- Old Inno installer cannot upgrade-in-place to NSIS: release notes tell v2 users to uninstall
  v2 once (their settings/history live in `~/.file-converter-pro` and are untouched; the new
  app reads app-data equivalents — one-time import of v2 settings/history if present).
- README fully rewritten; new screenshots after UI lands; version 3.0.0.

## 9. Accepted trade-offs
- Installer ~100–140 MB compressed (ffmpeg+pandoc+typst+pdfium is the honest price of 178
  standalone paths; same shape as the PyInstaller build). Post-v1: custom-trimmed ffmpeg.
- PDF→DOCX is text-fidelity (true of every non-Acrobat tool) — labeled in UI.
- Publisher name on Windows shows "SignPath Foundation" until/unless a paid personal cert is chosen.
- First-ever downloads of a brand-new file hash can still occasionally warn in browsers
  (per-hash reputation); fades with downloads, mitigated by timestamping + stable identity.
