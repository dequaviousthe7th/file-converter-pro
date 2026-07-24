# File Converter Pro 3.0 Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild File Converter Pro as a Tauri 2 app — Rust conversion engine (178+ pairs), one premium React UI, standalone sidecars, signed CI releases.

**Architecture:** Cargo workspace: `crates/engine` (fcp-engine, pure Rust, no Tauri/GTK deps, fully testable on WSL2) + `src-tauri` (thin shell: commands, job registry, channels) + `src` (React 19/Vite/Tailwind v4 frontend). Sidecars (ffmpeg/pandoc/typst) and pdfium fetched by script, bundled per-target by Tauri.

**Tech Stack:** Tauri 2.11.x, React 19 + TS + Vite 7 + Tailwind v4 + shadcn-style components + motion; Rust: image 0.25, fast_image_resize 6, webp 0.3, ico-builder 0.2, resvg 0.47, svg2pdf 0.13, printpdf =0.12.4, pdfium-render 0.9.3, pdf-extract 0.12 (fallback), csv 1.4, calamine 0.36, rust_xlsxwriter 0.96, serde_json (preserve_order), serde-saphyr, toml 1.1.

**Reference:** design doc `docs/superpowers/specs/2026-07-25-tauri-rebuild-design.md`; old-app parity inventory is authoritative for the format matrix and media parameters (reproduced below where needed).

---

## Shared contracts (ALL tasks must match these exactly)

### Engine public API (`crates/engine/src/lib.rs`)

```rust
pub mod registry;   // format matrix
pub mod error;      // ConvertError
pub mod job;        // CancelToken, ProgressFn
pub mod options;    // ConvertOptions, Sidecars
pub mod convert;    // dispatch entry point
// domain modules (private behind convert::dispatch): images, svg, data, config,
// documents, media (audio+video+heic+gif), pdfgen (image->pdf)

// error.rs
#[derive(Debug, thiserror::Error)]
#[error("{message}")]
pub struct ConvertError { pub message: String, pub detail: Option<String> }
impl ConvertError { pub fn new(msg: impl Into<String>) -> Self; pub fn with_detail(msg: impl Into<String>, detail: impl Into<String>) -> Self; }

// job.rs
#[derive(Clone, Default)]
pub struct CancelToken(std::sync::Arc<std::sync::atomic::AtomicBool>);
impl CancelToken {
    pub fn cancel(&self); pub fn is_cancelled(&self) -> bool;
    pub fn check(&self) -> Result<(), ConvertError>; // Err("Conversion cancelled") if set
}
pub type ProgressFn<'a> = &'a (dyn Fn(u8, &str) + Send + Sync); // (percent 0-100, message)

// options.rs
#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct ConvertOptions { pub image_quality: u8, pub audio_bitrate: String, pub pdf_dpi: u32 }
impl Default for ConvertOptions { /* 85, "192k", 144 */ }
#[derive(Clone, Default)]
pub struct Sidecars { pub ffmpeg: Option<std::path::PathBuf>, pub pandoc: Option<std::path::PathBuf>, pub typst: Option<std::path::PathBuf>, pub pdfium: Option<std::path::PathBuf> }

// convert.rs
pub struct ConversionRequest { pub input: std::path::PathBuf, pub target: String, pub output_dir: std::path::PathBuf, pub options: ConvertOptions }
/// Returns produced output paths (usually 1; N for pdf->image pages).
pub fn convert(req: &ConversionRequest, sidecars: &Sidecars, cancel: &CancelToken, progress: ProgressFn) -> Result<Vec<std::path::PathBuf>, ConvertError>;
/// `{stem}_converted.{ext}`, then " (1)", " (2)"... if exists. Pub for reuse + tests.
pub fn unique_output_path(output_dir: &std::path::Path, stem: &str, ext: &str) -> std::path::PathBuf;

// registry.rs
#[derive(Clone, Copy, PartialEq, serde::Serialize)]
pub enum Category { Documents, Images, Audio, Video, Data, Config }
#[derive(Clone, serde::Serialize)]
pub struct FormatInfo { pub ext: &'static str, pub name: &'static str, pub category: Category, pub targets: &'static [&'static str] }
pub fn formats() -> &'static [FormatInfo];
pub fn normalize_ext(ext: &str) -> &str; // jpeg->jpg, tif->tiff, yml->yaml, htm->html (registry stores canonical only; UI accepts aliases)
pub fn format_for(ext: &str) -> Option<&'static FormatInfo>;
pub fn is_supported(ext: &str) -> bool;
```

### Tauri IPC (frontend/backend contract)

Commands (src-tauri/src/commands.rs):
- `get_formats() -> Vec<FormatInfo>`
- `probe_file(path: String) -> FileMeta` → `{ ext, name, sizeBytes, sizeLabel, formatName, category, targets }` (error string if unsupported)
- `start_job(input: String, target: String, onEvent: Channel<JobEvent>) -> u64` (jobId; reads settings itself)
- `cancel_job(job_id: u64)`, `cancel_all()`
- `get_settings() -> Settings` / `set_settings(s: Settings)` — `{ outputDir, afterConversion: "ask"|"open_folder"|"notify", imageQuality, audioBitrate, pdfDpi }` (camelCase via serde rename_all)
- `get_history(limit: u32) -> Vec<HistoryRecord>` / `clear_history()` — record `{ source, output, sourceName, outputName, timestamp, datetime, status, duration }` (v2 schema, camelCase)
- `open_path(path: String)` / `reveal_path(path: String)` (tauri-plugin-opener)
- `pick_files() -> Vec<String>` / `pick_folder() -> Option<String>` (dialog)

JobEvent (channel payload, serde camelCase):
```rust
#[derive(Clone, serde::Serialize)]
#[serde(rename_all = "camelCase", tag = "state")]
pub enum JobEvent {
    Running { pct: u8, message: String },
    Done { outputs: Vec<String>, duration: f64 },
    Failed { message: String, detail: Option<String> },
    Cancelled,
}
```

Frontend mirrors these in `src/lib/types.ts`. Job queue lives in the FRONTEND (Zustand store): it feeds files one at a time to `start_job` sequentially — engine/back end stays queue-agnostic (simpler than v2's BatchConverter; per-item cancel = cancel that job; done items are never re-run).

### Format matrix (registry.rs — canonical, from v2 config.py + design deltas)

Documents: pdf→[docx,txt,md,png,jpg,html]; docx→[pdf,txt,md,html]; md→[pdf,docx,txt,html]; txt→[pdf,docx,md]; html→[pdf,docx,txt,md]; rtf→[pdf,docx,txt]; epub→[pdf,txt,docx]
Images: png→[jpg,webp,bmp,pdf,tiff,ico,gif]; jpg→[png,webp,bmp,pdf,tiff,ico,gif]; webp→[png,jpg,bmp,pdf,tiff,gif]; bmp→[png,jpg,webp,pdf,tiff,gif]; tiff→[png,jpg,webp,bmp,pdf,gif]; gif→[png,jpg,webp,bmp,pdf]; ico→[png,jpg,bmp]; svg→[png,jpg,webp,pdf]; heic→[png,jpg,webp,bmp,pdf,tiff]
Audio: mp3→[wav,flac,ogg,aac,m4a,wma]; wav→[mp3,flac,ogg,aac,m4a]; flac→[mp3,wav,ogg,aac,m4a]; ogg→[mp3,wav,flac,aac,m4a]; aac→[mp3,wav,flac,ogg,m4a]; m4a→[mp3,wav,flac,ogg,aac]; wma→[mp3,wav,flac,ogg,m4a]
Video: mp4/avi/mkv/mov/webm → the other four + gif
Data: csv→[xlsx,json,tsv,html]; xlsx→[csv,json,tsv,html]; json→[csv,xlsx,yaml,toml,tsv]; tsv→[csv,xlsx,json]
Config: yaml→[json,toml]; toml→[json,yaml]
Aliases (inputs only): jpeg→jpg, tif→tiff, yml→yaml, heif→heic, htm→html.

### Media parameters (v2 parity — do not deviate)

- ffmpeg audio: mp3=libmp3lame; wav=pcm_s16le; flac=flac; ogg=libvorbis; aac=`-f adts` aac; m4a=`-f ipod` aac; wma=`-f asf` wmav2. `-b:a {audio_bitrate}` for mp3/ogg/aac/m4a/wma; `-map_metadata 0`.
- ffmpeg video: mp4=`-c:v libx264 -c:a aac -movflags +faststart`; mov same; avi=`-c:v libx264 -c:a mp3`; mkv=`-c:v libx264 -c:a aac`; webm=`-c:v libvpx-vp9 -b:v 2M -c:a libopus`.
- video→gif: two-pass. P1 `-vf "fps=10,scale=480:-1:flags=lanczos,palettegen" {tmp}.palette.png`; P2 `-i in -i palette -lavfi "fps=10,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse"`. Palette in temp dir, removed after.
- Progress: spawn with `-progress pipe:1 -nostats -y -hide_banner`; parse `out_time_ms=`/`out_time=` lines ÷ input duration (duration from `ffmpeg -i` stderr `Duration: HH:MM:SS.ss`). Map to 5–95%. Windows: CREATE_NO_WINDOW (0x08000000) via `std::os::windows::process::CommandExt::creation_flags` behind `#[cfg(windows)]`.
- Images: JPEG `quality=options.image_quality`; WebP lossy `quality`; TIFF LZW; PNG default; ICO sizes [16,24,32,48,64,128,256] via ico-builder; alpha composited over white for jpg/bmp targets; apply EXIF orientation on decode.
- pandoc: `pandoc {in} -o {out}` (+`--standalone` for html output; `--pdf-engine={typst_path}` when target=pdf). 120s timeout wrapper, kill on cancel.
- PDF render: pdfium at `options.pdf_dpi` (default 144); multi-page → `{stem}_converted_page{N}.{ext}` each unique-suffixed.

---

### Task 1: Scaffold workspace + frontend + Tauri shell

**Files:** Create root `Cargo.toml` (workspace members `crates/engine`, `src-tauri`), `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx`, `src/App.tsx` (placeholder), `src/styles.css` (Tailwind v4 `@import "tailwindcss"`), `crates/engine/Cargo.toml` + `src/lib.rs` (stub), `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`, `src-tauri/capabilities/default.json`, `src-tauri/src/main.rs`+`lib.rs`, `src-tauri/build.rs`, `.gitignore` additions (node_modules, dist-web, target, src-tauri/binaries, src-tauri/resources/pdfium*, src-tauri/gen).

- [ ] npm deps: react@19 react-dom@19, @tauri-apps/api@^2, plugins (dialog, opener, store, shell), dev: vite@7, @vitejs/plugin-react, typescript, tailwindcss@4, @tailwindcss/vite, motion, zustand, lucide-react, clsx, tailwind-merge, @types/react(-dom)
- [ ] `tauri.conf.json`: productName "File Converter Pro", identifier `com.dequavious.fileconverterpro`, version 3.0.0, window 1100x740 min 900x640, `decorations: false`, frontendDist `../dist-web`, devUrl http://localhost:1420; bundle: targets nsis+dmg+appimage+deb, externalBin `["binaries/ffmpeg","binaries/pandoc","binaries/typst"]`, resources `["resources/*"]`, icons from assets/logo (Task 12 generates .icns/.ico set via `tauri icon`); nsis `installMode: currentUser`
- [ ] capabilities/default.json: core defaults + dialog, opener (open/reveal), store, shell sidecar spawn for the three binaries + core:window (drag/minimize/maximize/close)
- [ ] Verify: `npm run build` (tsc+vite OK), `cargo check -p fcp-engine` OK. (`cargo check -p file-converter-pro` needs GTK — CI-only; do not block on it locally.)
- [ ] Commit "scaffold"

### Task 2: Engine core — error, job, options, registry, unique paths

**Files:** Create `crates/engine/src/{error,job,options,registry,convert}.rs`; Test: `crates/engine/tests/registry.rs`, `tests/naming.rs`.

- [ ] Write failing tests: registry pair counts (pdf has 6 targets; every target of every format is itself a known format or in {png,jpg,gif,pdf,html,docx,txt,md...}; alias normalization jpeg→jpg etc.; is_supported("JPEG") case-insensitive), unique_output_path creates `_converted` name then ` (1)` when file exists (use tempdir)
- [ ] Implement per shared contracts; matrix verbatim from "Format matrix" section; `convert()` dispatches on (normalized source ext, target) to domain stubs returning `Err(ConvertError::new("not implemented"))`
- [ ] `cargo test -p fcp-engine` green; commit "engine core"

### Task 3: Engine — images + svg + image→pdf

**Files:** Create `crates/engine/src/images.rs`, `svg.rs`, `pdfgen.rs`; Test: `tests/images.rs` (generate fixtures with the image crate in tests — 4x4 RGBA PNG, JPEG, BMP, tiny SVG string, 2-frame GIF).

- [ ] Failing tests: png→jpg (output exists, decodable, RGB, white-composited), png→ico (contains 256px entry), jpg quality honored (q=10 file smaller than q=95), svg→png renders non-empty, png→pdf produces valid PDF header `%PDF`, tiff LZW roundtrip, gif first-frame→png
- [ ] Implement: decode via image crate (+EXIF orientation via `kamadak-exif` on jpg/tiff), encode per media-parameters table; resize only for ICO (fast_image_resize); svg via resvg→pixmap→image, svg→pdf via svg2pdf; image→pdf via printpdf (A4, 36pt margins, aspect-fit, JPEG pass-through)
- [ ] Animated gif→(png/jpg/webp/bmp): first frame in-process. gif→pdf same. (Animated fidelity paths go through ffmpeg in Task 6 only for video→gif; gif inputs stay in-process — v2 parity.)
- [ ] heic→X: in images.rs but requires sidecars.ffmpeg: `ffmpeg -i in.heic tmp.png` then in-process to target; clear error "HEIC support requires the bundled ffmpeg" if sidecar missing
- [ ] Tests green; commit "images"

### Task 4: Engine — data (csv/tsv/xlsx/json tables)

**Files:** Create `crates/engine/src/data.rs`; Test: `tests/data.rs`.

- [ ] Failing tests: csv→json records orient (`[{"a":"1","b":"x"}]`), csv→xlsx then calamine reads back same cells, json(array-of-objects)→csv headers union-ordered by first appearance, tsv delimiter, xlsx→html contains `<table`, json nested → uses serde_json to flatten one level like v2's json_normalize? NO — v2 used pandas; simplify: array-of-objects required, nested values serialized as JSON strings (documented deviation), dict-root → find first array-of-objects value else error
- [ ] Implement with csv/calamine/rust_xlsxwriter/serde_json; HTML output = v2-style styled page (#4a90d9 header, zebra rows); all reads utf-8 lossy
- [ ] Tests green; commit "data"

### Task 5: Engine — config hub (json/yaml/toml)

**Files:** Create `crates/engine/src/config.rs`; Test: `tests/config.rs`.

- [ ] Failing tests: yaml→json preserves key order; json→toml with null → ConvertError mentioning the key path; json array-root→toml → clear error; toml datetime→json becomes RFC3339 string; yaml `no:` stays string "no" (YAML 1.2); json→yaml unicode preserved
- [ ] Implement via serde_json::Value hub (preserve_order); serde-saphyr for yaml in/out; toml crate; explicit edge handling per design §4.2
- [ ] Tests green; commit "config"

### Task 6: Engine — sidecar runner + audio/video/gif

**Files:** Create `crates/engine/src/sidecar.rs` (spawn/timeout/kill-on-cancel/CREATE_NO_WINDOW, stdout+stderr capture), `media.rs`; Test: `tests/media.rs` — tests run ONLY if `std::env::var("FCP_FFMPEG")` or system ffmpeg exists (generate 1s test tone wav via ffmpeg itself; skip silently otherwise so CI-without-ffmpeg passes).

- [ ] sidecar.rs: `pub fn run(bin: &Path, args: &[OsString], cancel: &CancelToken, timeout: Duration, on_line: impl FnMut(&str)) -> Result<Output, ConvertError>` — poll child with 100ms ticks, kill+wait on cancel/timeout (fixes v2 orphan bug), read stderr+stdout on threads
- [ ] media.rs: duration probe (parse `Duration:` from `ffmpeg -i` stderr), audio/video arg builders per media-parameters table, progress mapping 5–95%, video→gif two-pass with palette temp cleanup, wav→mp3 test asserts output >1KB and progress reached ≥95
- [ ] Cancel test: start slow conversion, cancel at 200ms, assert child gone (`kill` returns) and partial output removed
- [ ] Tests green (with local /usr/bin/ffmpeg); commit "media"

### Task 7: Engine — documents (pandoc/typst/pdfium)

**Files:** Create `crates/engine/src/documents.rs`, `pdf.rs` (pdfium wrapper: lazy bind from Sidecars.pdfium path, text extraction, page render); Test: `tests/documents.rs` — pandoc/typst tests gated on env `FCP_PANDOC`/`FCP_TYPST` or PATH presence (skip otherwise); pdfium tests gated on `FCP_PDFIUM`.

- [ ] documents.rs routes: {md,html,docx,rtf,epub,txt}×{md,html,docx,rtf,epub,txt}\{same} via pandoc (txt output = `-t plain`; html output `--standalone`); X→pdf via pandoc `--pdf-engine={typst}`; txt→{pdf,docx,md} — md via small in-process writer (v2 parity: `# {filename}` header + escaped body) to avoid pandoc dependency for the trivial case; pdf→txt/md via pdf.rs extraction (md = txt + `# {filename}` header, v2 parity); pdf→docx = extraction→temp .md→pandoc; pdf→html = extracted text in v2-style boilerplate page; pdf→png/jpg = render all pages at options.pdf_dpi
- [ ] pdf.rs: `Pdfium::bind_to_library(path)`; fallback to `pdf-extract` crate for text when pdfium missing; page render → image crate encode
- [ ] Failing→green tests: md→html contains `<h1`, html→md contains `#`, pdf fixture (generate via printpdf in-test) →txt contains known string, →png produces page1 file; commit "documents"

### Task 8: Tauri shell — state, jobs, commands, settings, history

**Files:** Create `src-tauri/src/{lib,main,commands,jobs,settings,history,sidecars}.rs`.

- [ ] sidecars.rs: resolve ffmpeg/pandoc/typst via `app.shell().sidecar()`-style path resolution (`tauri::process::current_binary` dir + target-triple names) with dev fallback to PATH; pdfium from `app.path().resource_dir()/pdfium/`; expose `Sidecars` for engine. Dev mode: also honor env overrides FCP_FFMPEG etc.
- [ ] jobs.rs: `JobRegistry { next_id: AtomicU64, jobs: Mutex<HashMap<u64, CancelToken>> }`; start_job spawns `tauri::async_runtime::spawn_blocking`: probe → engine::convert with progress closure sending `JobEvent::Running` over the Channel (throttle to ≥1% deltas or 100ms) → Done/Failed/Cancelled event → history record (ALL jobs recorded — fixes v2 gap) → after_conversion behavior handled frontend-side from settings
- [ ] settings.rs: tauri-plugin-store `settings.json` in appDataDir; defaults per contract; one-time import from v2 `~/.file-converter-pro/settings.json` + `history.json` if store empty (map old keys; drop last_ui/theme)
- [ ] history.rs: JSON file in appDataDir, newest-first, cap 200, same record schema
- [ ] Window control commands OR use core:window plugin permissions from JS (choose JS: `getCurrentWindow().minimize()` etc.)
- [ ] On app exit (`RunEvent::ExitRequested`): cancel_all + kill children
- [ ] Verify `cargo check -p file-converter-pro` compiles in CI mindset (locally OK to rely on `cargo check -p fcp-engine` only); commit "shell"

### Task 9: Frontend — design system + app shell

**Files:** Create `src/styles.css` (design tokens), `src/components/{Titlebar,Nav,Toast,Progress,Button,...}.tsx`, `src/lib/{types,ipc,store}.ts`, `src/App.tsx`.

- [ ] MUST load `frontend-design` skill before writing UI code. Brand: charcoal #0f1115–#16181d surfaces, teal #00d4aa accent (hover #2ee6a8), Inter/system font stack, 8px radius cards, subtle borders (#ffffff0d), motion springs for state changes. Custom titlebar: logo + "File Converter Pro", drag region, min/max/close (hover states, close=red), platform-aware (hide custom controls on macOS overlay style optional — keep custom on all for v1 consistency)
- [ ] Nav: left rail (Convert / History / Settings) with icons + active accent indicator + format-count footer badge
- [ ] store.ts (zustand): files queue [{id, path, meta, target, status, pct, message, outputs}], settings cache, history cache; ipc.ts wraps all commands with typed signatures from contract
- [ ] `npm run build` clean; commit "ui shell"

### Task 10: Frontend — Convert view

**Files:** Create `src/views/Convert.tsx`, `src/components/{DropZone,FileRow,TargetPicker,CategoryPill}.tsx`.

- [ ] Empty state: hero drop-zone card (dashed ring, + icon, "Drop files or browse", category pills, Browse button → pick_files)
- [ ] OS drag-drop: `getCurrentWebview().onDragDropEvent` — enter/over → full-surface overlay highlight; drop → probe each path, add rows (dedupe by path+eventId — known Tauri duplicate-event bug #14134); unsupported ext → toast error ".xyz files are not supported"
- [ ] Rows: ext badge (category-colored), name, formatName · size; TargetPicker dropdown (targets from meta; smart default = first target; "Apply to all compatible" action); status area morphs: picker → progress bar+% + message → done (Open / Show in Folder buttons) / failed (message, retry) / cancelled; remove-x while idle
- [ ] Convert All: sequential `start_job` per idle row (skip done — fixes v2 re-convert bug); per-row Cancel + global Cancel All; after each Done apply settings.afterConversion: "ask"=toast with Open Folder/Open File actions (10s), "open_folder"=reveal once per batch end, "notify"=tauri notification
- [ ] `npm run build` clean; commit "convert view"

### Task 11: Frontend — History + Settings views

**Files:** Create `src/views/History.tsx`, `src/views/Settings.tsx`.

- [ ] History: table (source, output, status pill OK/Fail, date, duration), row actions open/reveal (disabled if file gone), Clear All with confirm, empty state
- [ ] Settings cards: Output Folder (path display + Change → pick_folder); After Conversion radio (ask/open_folder/notify); Image Quality slider 10–100 with live %; Audio Bitrate segmented 128k/192k/256k/320k; PDF render DPI select (96/144/300); Reset All. Every control persists via set_settings immediately and is ACTUALLY consumed by jobs (fixes v2 dead knobs)
- [ ] About footer: version, author link, "Open Source Licenses" (modal listing bundled components + licenses dir reference)
- [ ] `npm run build` clean; commit "views"

### Task 12: Sidecar fetch scripts + icons + licenses

**Files:** Create `scripts/fetch-sidecars.sh` (bash, takes target triple arg; used by CI + local Linux dev), `scripts/fetch-sidecars.ps1` (Windows CI), `licenses/{README.md,LICENSE.ffmpeg.txt,LICENSE.pandoc.txt,LICENSE.typst.txt,LICENSE.pdfium.txt}`.

- [ ] Script sources (pin exact versions in a VERSIONS block at top): ffmpeg 8.1.x — BtbN win64-gpl zip / linux64-gpl tar.xz, martin-riedl.de release for macos arm64+x64; pandoc 3.10.1 per-OS from jgm/pandoc releases; typst 0.15.1 from typst/typst releases; pdfium latest bblanchon non-V8 per-OS → `src-tauri/resources/pdfium/`. Outputs into `src-tauri/binaries/{name}-{target-triple}[.exe]`, chmod +x, verify sha256 where published, strip to just the needed binary (no ffprobe/ffplay)
- [ ] `npx tauri icon assets/logo.png` → src-tauri/icons committed
- [ ] licenses/README.md: component, exact version, license, source URL table
- [ ] Local verify: `bash scripts/fetch-sidecars.sh x86_64-unknown-linux-gnu` populates binaries/ (run it; sizes sane); commit "sidecars + icons" (scripts and licenses only; binaries gitignored)

### Task 13: CI — ci.yml + release.yml with signing hooks

**Files:** Create `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `docs/RELEASING.md`.

- [ ] ci.yml (push/PR): job test-engine (ubuntu; cargo fmt --check, clippy -D warnings, cargo test -p fcp-engine with apt ffmpeg+pandoc for gated tests); job frontend (npm ci, tsc, vite build); job check-tauri (ubuntu-22.04 with webkit2gtk apt deps, cargo check --workspace)
- [ ] release.yml (tag `v*` push or workflow_dispatch): matrix {windows-latest x86_64-pc-windows-msvc, macos-latest aarch64-apple-darwin, macos-latest x86_64-apple-darwin, ubuntu-22.04 x86_64-unknown-linux-gnu}; steps: checkout → rust+node setup → fetch-sidecars for triple → tauri-apps/tauri-action@v0 (draft release, `File Converter Pro v__VERSION__`) with env: APPLE_CERTIFICATE/_PASSWORD/APPLE_SIGNING_IDENTITY/APPLE_API_KEY/_ISSUER/_KEY_PATH guarded by `secrets.APPLE_CERTIFICATE != ''`; Windows: after unsigned build, conditional SignPath steps (`if: vars.SIGNPATH_ORG_ID != ''`): upload installer artifact → signpath/github-action-submit-signing-request (wait) → replace asset on release; Linux job appends SHA256SUMS (+ GPG sign if `secrets.GPG_PRIVATE_KEY` present)
- [ ] docs/RELEASING.md: exact release runbook (bump versions in tauri.conf.json+Cargo.toml+package.json, tag, approve SignPath request, publish draft)
- [ ] Validate YAML (actionlint if available / yq parse); commit "ci"

### Task 14: Docs — README, SIGNING, BUILDING + repo hygiene

**Files:** Rewrite `README.md`; Create `docs/SIGNING.md`, `docs/BUILDING.md`, `CHANGELOG.md`, `.github/signing-policy.md` (SignPath requirement); Modify `.gitignore`.

- [ ] README: hero (logo, badges v3.0.0 / MIT / platforms / 178+ paths), download table per OS with file names, "Why no warnings" trust section (signed releases + verify checksums), format matrix tables (regenerate from registry — keep accurate: 178 pairs not "200+"), features, screenshots placeholders, build-from-source short section pointing to docs/BUILDING.md, v2→v3 migration note (uninstall v2; settings auto-imported)
- [ ] docs/SIGNING.md: step-by-step enrollment — SignPath Foundation application checklist (policy page link, MFA, what to enter, expected wait), Apple Developer enrollment + cert/App-Store-Connect-key creation + exact GitHub secret names, Certum/Azure fallbacks with current prices, table of ALL GitHub secrets/vars the workflows read
- [ ] docs/BUILDING.md: prerequisites per OS (incl. WSL2 apt line), dev loop (`npm run tauri dev`), sidecar fetch, engine tests
- [ ] CHANGELOG.md: 3.0.0 entry (rewrite highlights, fixed v2 bugs list)
- [ ] Commit "docs"

### Task 15: Remove legacy Python + final verification

**Files:** Delete `app.py`, `app_simple.py`, `config.py`, `requirements.txt`, `START.bat`, `START_SIMPLE.bat`, `backend/`, `utils/`, `installer/`, `coverage/`, `converted/`, `graphify-out/`, stray `dist/`; keep `assets/` (logo + screenshots until replaced), `LICENSE`.

- [ ] `git rm` the above; ensure .gitignore covers converted/, dist/, graphify-out/
- [ ] Full verification: `cargo test -p fcp-engine` all green; `cargo fmt --check`; `clippy -D warnings` on engine; `npm run build` clean; fetch-sidecars script re-run OK
- [ ] Commit "remove legacy implementation"
- [ ] Write vault session note per CLAUDE.md

---

## Self-review notes
- Spec coverage: §4 matrix→Tasks 2–7; §4.3 jobs→Task 8; §5 UI→Tasks 9–11; §6 distribution/signing→Tasks 12–13; §7 testing→per-task + Task 13; §8 migration→Tasks 8 (import), 14 (README), 15 (removal). ✓
- Type consistency: JobEvent/Settings/HistoryRecord/FormatInfo defined once in Shared Contracts; all tasks reference those. ✓
- Known intentional deviations from v2 (documented in design doc §4.1/§5): per-file targets instead of union menu; JSON table flattening simplified vs pandas json_normalize; real pdf→image.
