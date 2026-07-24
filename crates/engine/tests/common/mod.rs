//! Shared test helper: locates (or downloads) the pandoc / typst / pdfium
//! tools the gated document tests need. Returns `None` when a tool cannot be
//! obtained so callers can skip gracefully (CI without network still passes).

use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::OnceLock;

use fcp_engine::options::Sidecars;

const TOOLS_DIR: &str =
    "/tmp/claude-1000/-home-dequavious-File-Converter/3447226d-dfef-4cb3-a46a-9900af5c6e1e/scratchpad/tools";

const PANDOC_URL: &str =
    "https://github.com/jgm/pandoc/releases/download/3.10.1/pandoc-3.10.1-linux-amd64.tar.gz";
const PANDOC_MEMBER: &str = "pandoc-3.10.1/bin/pandoc";

const TYPST_URL: &str =
    "https://github.com/typst/typst/releases/download/v0.15.1/typst-x86_64-unknown-linux-musl.tar.xz";
const TYPST_MEMBER: &str = "typst-x86_64-unknown-linux-musl/typst";

const PDFIUM_URL: &str =
    "https://github.com/bblanchon/pdfium-binaries/releases/latest/download/pdfium-linux-x64.tgz";
const PDFIUM_MEMBER: &str = "lib/libpdfium.so";

/// Locate or download pandoc 3.10.1, typst 0.15.1 and pdfium (linux-x64).
///
/// Resolution order per tool: env override (`FCP_PANDOC` / `FCP_TYPST` /
/// `FCP_PDFIUM`) → cached copy in the scratchpad tools dir → download
/// (curl, one retry) → `PATH` (executables only). `None` on any failure.
pub fn ensure_tools() -> Option<Sidecars> {
    static TOOLS: OnceLock<Option<Sidecars>> = OnceLock::new();
    TOOLS.get_or_init(build).clone()
}

fn build() -> Option<Sidecars> {
    let dir = PathBuf::from(TOOLS_DIR);
    std::fs::create_dir_all(&dir).ok()?;
    let pandoc = tool(
        &dir,
        "pandoc",
        "FCP_PANDOC",
        PANDOC_URL,
        PANDOC_MEMBER,
        true,
    )?;
    let typst = tool(&dir, "typst", "FCP_TYPST", TYPST_URL, TYPST_MEMBER, true)?;
    let pdfium = tool(
        &dir,
        "libpdfium.so",
        "FCP_PDFIUM",
        PDFIUM_URL,
        PDFIUM_MEMBER,
        false,
    )?;
    Some(Sidecars {
        ffmpeg: None,
        pandoc: Some(pandoc),
        typst: Some(typst),
        pdfium: Some(pdfium),
    })
}

fn tool(
    dir: &Path,
    name: &str,
    env: &str,
    url: &str,
    member: &str,
    is_executable: bool,
) -> Option<PathBuf> {
    if let Ok(overridden) = std::env::var(env) {
        let p = PathBuf::from(overridden);
        if p.exists() {
            return Some(p);
        }
    }
    let cached = dir.join(name);
    if cached.exists() {
        return Some(cached);
    }
    if let Some(downloaded) = download_and_extract(dir, name, url, member) {
        return Some(downloaded);
    }
    if is_executable {
        if let Ok(out) = Command::new("which").arg(name).output() {
            if out.status.success() {
                let p = String::from_utf8_lossy(&out.stdout).trim().to_string();
                if !p.is_empty() {
                    return Some(PathBuf::from(p));
                }
            }
        }
    }
    None
}

fn download_and_extract(dir: &Path, name: &str, url: &str, member: &str) -> Option<PathBuf> {
    let archive = dir.join(format!("{name}.download"));
    if !download(url, &archive) {
        return None;
    }
    let extracted = Command::new("tar")
        .arg("-xf")
        .arg(&archive)
        .arg("-C")
        .arg(dir)
        .arg(member)
        .status()
        .map(|s| s.success())
        .unwrap_or(false);
    let _ = std::fs::remove_file(&archive);
    if !extracted {
        return None;
    }
    let dest = dir.join(name);
    std::fs::rename(dir.join(member), &dest).ok()?;
    if let Some(top) = member.split('/').next() {
        if top != name {
            let _ = std::fs::remove_dir_all(dir.join(top));
        }
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(&dest, std::fs::Permissions::from_mode(0o755));
    }
    Some(dest)
}

/// Fetch `url` to `dest` with curl; one retry on failure.
fn download(url: &str, dest: &Path) -> bool {
    for _ in 0..2 {
        let ok = Command::new("curl")
            .args([
                "-fsSL",
                "--connect-timeout",
                "30",
                "--max-time",
                "600",
                "-o",
            ])
            .arg(dest)
            .arg(url)
            .status()
            .map(|s| s.success())
            .unwrap_or(false);
        if ok {
            return true;
        }
        let _ = std::fs::remove_file(dest);
    }
    false
}
