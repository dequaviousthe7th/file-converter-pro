//! Tauri IPC commands — the exact names/shapes the frontend codes against.

use std::path::Path;

use fcp_engine::registry::{self, Category, FormatInfo};
use serde::Serialize;
use tauri::ipc::Channel;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_opener::OpenerExt;

use crate::history::{self, HistoryRecord};
use crate::jobs::{self, JobEvent, JobRegistry};
use crate::settings::{self, Settings};

/// `{ ext, name, sizeBytes, sizeLabel, formatName, category, targets }`
#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct FileMeta {
    pub ext: String,
    pub name: String,
    pub size_bytes: u64,
    pub size_label: String,
    pub format_name: String,
    pub category: Category,
    pub targets: Vec<String>,
}

#[tauri::command]
pub fn get_formats() -> Vec<FormatInfo> {
    registry::formats().to_vec()
}

#[tauri::command]
pub fn probe_file(path: String) -> Result<FileMeta, String> {
    let file = Path::new(&path);
    let metadata = std::fs::metadata(file).map_err(|_| format!("File not found: {path}"))?;
    if !metadata.is_file() {
        return Err(format!("Not a file: {path}"));
    }
    let name = file
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_default();
    let raw_ext = file
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or_default();
    if raw_ext.is_empty() {
        return Err(format!("{name} has no file extension"));
    }
    let format = registry::format_for(raw_ext)
        .ok_or_else(|| format!(".{} files are not supported", raw_ext.to_ascii_lowercase()))?;
    Ok(FileMeta {
        ext: format.ext.to_string(),
        name,
        size_bytes: metadata.len(),
        size_label: humanize_size(metadata.len()),
        format_name: format.name.to_string(),
        category: format.category,
        targets: format.targets.iter().map(|t| t.to_string()).collect(),
    })
}

#[tauri::command]
pub async fn start_job(
    app: AppHandle,
    input: String,
    target: String,
    on_event: Channel<JobEvent>,
) -> Result<u64, String> {
    jobs::start(app, input, target, on_event)
}

#[tauri::command]
pub fn cancel_job(registry: State<'_, JobRegistry>, job_id: u64) {
    registry.cancel(job_id);
}

#[tauri::command]
pub fn cancel_all(registry: State<'_, JobRegistry>) {
    registry.cancel_all();
}

#[tauri::command]
pub fn get_settings(app: AppHandle) -> Result<Settings, String> {
    settings::load(&app)
}

#[tauri::command]
pub fn set_settings(app: AppHandle, s: Settings) -> Result<(), String> {
    settings::save(&app, &s)
}

#[tauri::command]
pub fn get_history(app: AppHandle, limit: u32) -> Vec<HistoryRecord> {
    history::load(&app, limit as usize)
}

#[tauri::command]
pub fn clear_history(app: AppHandle) -> Result<(), String> {
    history::clear(&app)
}

#[tauri::command]
pub fn open_path(app: AppHandle, path: String) -> Result<(), String> {
    app.opener()
        .open_path(path, None::<&str>)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn reveal_path(app: AppHandle, path: String) -> Result<(), String> {
    app.opener()
        .reveal_item_in_dir(&path)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn pick_files(app: AppHandle) -> Result<Vec<String>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let mut builder = app.dialog().file().set_title("Choose files to convert");
        for (name, extensions) in dialog_filters() {
            let refs: Vec<&str> = extensions.iter().map(String::as_str).collect();
            builder = builder.add_filter(name, &refs);
        }
        builder
            .blocking_pick_files()
            .unwrap_or_default()
            .into_iter()
            .filter_map(|file| file.into_path().ok())
            .map(|path| path.to_string_lossy().into_owned())
            .collect()
    })
    .await
    .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn pick_folder(app: AppHandle) -> Result<Option<String>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        app.dialog()
            .file()
            .set_title("Choose output folder")
            .blocking_pick_folder()
            .and_then(|folder| folder.into_path().ok())
            .map(|path| path.to_string_lossy().into_owned())
    })
    .await
    .map_err(|e| e.to_string())
}

/// v2-style size label: bytes below 1 KB, otherwise one decimal.
fn humanize_size(bytes: u64) -> String {
    const KB: f64 = 1024.0;
    const MB: f64 = 1024.0 * 1024.0;
    const GB: f64 = 1024.0 * 1024.0 * 1024.0;
    let size = bytes as f64;
    if size < KB {
        format!("{bytes} B")
    } else if size < MB {
        format!("{:.1} KB", size / KB)
    } else if size < GB {
        format!("{:.1} MB", size / MB)
    } else {
        format!("{:.1} GB", size / GB)
    }
}

/// File-dialog filters built from the registry: "All Supported" (canonical
/// extensions + input aliases), one filter per category, then "All Files".
fn dialog_filters() -> Vec<(String, Vec<String>)> {
    const CATEGORY_ORDER: [Category; 6] = [
        Category::Documents,
        Category::Images,
        Category::Audio,
        Category::Video,
        Category::Data,
        Category::Config,
    ];
    // Input-only aliases (accepted by normalize_ext) users may pick.
    const ALIASES: [&str; 5] = ["jpeg", "tif", "yml", "heif", "htm"];

    let mut all: Vec<String> = Vec::new();
    let mut per_category: Vec<(Category, Vec<String>)> =
        CATEGORY_ORDER.iter().map(|c| (*c, Vec::new())).collect();

    let mut add = |category: Category, ext: &str, all: &mut Vec<String>| {
        all.push(ext.to_string());
        if let Some((_, extensions)) = per_category.iter_mut().find(|(c, _)| *c == category) {
            extensions.push(ext.to_string());
        }
    };
    for format in registry::formats() {
        add(format.category, format.ext, &mut all);
    }
    for alias in ALIASES {
        if let Some(format) = registry::format_for(alias) {
            add(format.category, alias, &mut all);
        }
    }

    let mut filters = vec![("All Supported".to_string(), all)];
    for (category, extensions) in per_category {
        if !extensions.is_empty() {
            filters.push((category_label(category).to_string(), extensions));
        }
    }
    filters.push(("All Files".to_string(), vec!["*".to_string()]));
    filters
}

fn category_label(category: Category) -> &'static str {
    match category {
        Category::Documents => "Documents",
        Category::Images => "Images",
        Category::Audio => "Audio",
        Category::Video => "Video",
        Category::Data => "Data",
        Category::Config => "Config",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn humanize_size_matches_v2_format() {
        assert_eq!(humanize_size(0), "0 B");
        assert_eq!(humanize_size(1023), "1023 B");
        assert_eq!(humanize_size(1024), "1.0 KB");
        assert_eq!(humanize_size(1536), "1.5 KB");
        assert_eq!(humanize_size(5 * 1024 * 1024), "5.0 MB");
        assert_eq!(humanize_size(3 * 1024 * 1024 * 1024), "3.0 GB");
    }

    #[test]
    fn dialog_filters_cover_registry_and_aliases() {
        let filters = dialog_filters();
        let (first_name, all) = &filters[0];
        assert_eq!(first_name, "All Supported");
        for ext in ["png", "pdf", "mp3", "mp4", "csv", "yaml"] {
            assert!(
                all.contains(&ext.to_string()),
                "All Supported missing {ext}"
            );
        }
        for alias in ["jpeg", "tif", "yml", "heif", "htm"] {
            assert!(
                all.contains(&alias.to_string()),
                "All Supported missing alias {alias}"
            );
        }
        let names: Vec<&str> = filters.iter().map(|(name, _)| name.as_str()).collect();
        assert_eq!(
            names,
            vec![
                "All Supported",
                "Documents",
                "Images",
                "Audio",
                "Video",
                "Data",
                "Config",
                "All Files"
            ]
        );
        assert_eq!(filters.last().unwrap().1, vec!["*".to_string()]);
        let images = &filters[2].1;
        assert!(images.contains(&"jpeg".to_string()));
        assert!(images.contains(&"heif".to_string()));
    }

    #[test]
    fn file_meta_serializes_camel_case() {
        let meta = FileMeta {
            ext: "png".into(),
            name: "a.png".into(),
            size_bytes: 2048,
            size_label: humanize_size(2048),
            format_name: "PNG".into(),
            category: Category::Images,
            targets: vec!["jpg".into()],
        };
        let value = serde_json::to_value(&meta).unwrap();
        let obj = value.as_object().unwrap();
        for key in [
            "ext",
            "name",
            "sizeBytes",
            "sizeLabel",
            "formatName",
            "category",
            "targets",
        ] {
            assert!(obj.contains_key(key), "missing key {key}");
        }
        assert_eq!(obj["sizeLabel"], "2.0 KB");
        assert_eq!(obj["category"], "Images");
    }
}
