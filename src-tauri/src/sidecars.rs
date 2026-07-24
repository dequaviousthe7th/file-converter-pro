//! Resolution of the bundled sidecar binaries (ffmpeg / pandoc / typst) and
//! the pdfium dynamic library.
//!
//! Resolution order for tools:
//! 1. Beside the app executable (Tauri sidecar convention — bundled builds
//!    place `ffmpeg[.exe]` next to the main binary; dev builds may keep the
//!    target-triple suffixed name).
//! 2. `FCP_FFMPEG` / `FCP_PANDOC` / `FCP_TYPST` environment overrides
//!    (dev convenience; ignored when the path does not exist).
//! 3. `PATH` lookup.
//!
//! pdfium: `FCP_PDFIUM` override, then `resource_dir()/pdfium/<platform lib>`.

use std::env;
use std::path::PathBuf;

use fcp_engine::options::Sidecars;
use tauri::{AppHandle, Manager, Runtime};

const EXE_SUFFIX: &str = if cfg!(windows) { ".exe" } else { "" };

fn pdfium_lib_name() -> &'static str {
    if cfg!(windows) {
        "pdfium.dll"
    } else if cfg!(target_os = "macos") {
        "libpdfium.dylib"
    } else {
        "libpdfium.so"
    }
}

/// Resolve every sidecar for the engine. Missing tools stay `None`; the
/// engine reports a clear error if a conversion actually needs them.
pub fn resolve<R: Runtime>(app: &AppHandle<R>) -> Sidecars {
    Sidecars {
        ffmpeg: resolve_tool("ffmpeg", "FCP_FFMPEG"),
        pandoc: resolve_tool("pandoc", "FCP_PANDOC"),
        typst: resolve_tool("typst", "FCP_TYPST"),
        pdfium: resolve_pdfium(app),
    }
}

fn resolve_tool(name: &str, env_var: &str) -> Option<PathBuf> {
    if let Some(found) = beside_executable(name) {
        return Some(found);
    }
    if let Some(overridden) = env::var_os(env_var).map(PathBuf::from) {
        if overridden.is_file() {
            return Some(overridden);
        }
    }
    find_in_path(name)
}

/// `{exe_dir}/{name}[.exe]`, falling back to the target-triple suffixed
/// name that `tauri dev` / fetch scripts use before bundling renames it.
fn beside_executable(name: &str) -> Option<PathBuf> {
    let exe = env::current_exe().ok()?;
    let dir = exe.parent()?;
    let plain = dir.join(format!("{name}{EXE_SUFFIX}"));
    if plain.is_file() {
        return Some(plain);
    }
    if let Ok(triple) = tauri::utils::platform::target_triple() {
        let suffixed = dir.join(format!("{name}-{triple}{EXE_SUFFIX}"));
        if suffixed.is_file() {
            return Some(suffixed);
        }
    }
    None
}

fn find_in_path(name: &str) -> Option<PathBuf> {
    let file = format!("{name}{EXE_SUFFIX}");
    let paths = env::var_os("PATH")?;
    env::split_paths(&paths)
        .map(|dir| dir.join(&file))
        .find(|candidate| candidate.is_file())
}

fn resolve_pdfium<R: Runtime>(app: &AppHandle<R>) -> Option<PathBuf> {
    if let Some(overridden) = env::var_os("FCP_PDFIUM").map(PathBuf::from) {
        if overridden.is_file() {
            return Some(overridden);
        }
    }
    let resource_dir = app.path().resource_dir().ok()?;
    let candidate = resource_dir.join("pdfium").join(pdfium_lib_name());
    candidate.is_file().then_some(candidate)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pdfium_lib_name_matches_platform() {
        let name = pdfium_lib_name();
        if cfg!(windows) {
            assert_eq!(name, "pdfium.dll");
        } else if cfg!(target_os = "macos") {
            assert_eq!(name, "libpdfium.dylib");
        } else {
            assert_eq!(name, "libpdfium.so");
        }
    }

    #[test]
    fn exe_suffix_matches_platform() {
        assert_eq!(EXE_SUFFIX, if cfg!(windows) { ".exe" } else { "" });
    }
}
