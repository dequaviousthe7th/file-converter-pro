//! Settings persisted with tauri-plugin-store (`settings.json` in the
//! app-data dir) plus a one-time import of v2's
//! `~/.file-converter-pro/settings.json` / `history.json`.

use std::fs;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use serde_json::Value;
use tauri::{AppHandle, Manager, Runtime};
use tauri_plugin_store::StoreExt;

use crate::history;

const STORE_FILE: &str = "settings.json";
const KEY: &str = "settings";

pub const AFTER_ASK: &str = "ask";
pub const AFTER_OPEN_FOLDER: &str = "open_folder";
pub const AFTER_NOTIFY: &str = "notify";

/// IPC settings shape (camelCase on the wire):
/// `{ outputDir, afterConversion, imageQuality, audioBitrate, pdfDpi }`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct Settings {
    pub output_dir: String,
    pub after_conversion: String,
    pub image_quality: u8,
    pub audio_bitrate: String,
    pub pdf_dpi: u32,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            output_dir: String::new(), // empty = resolved to the default dir on load
            after_conversion: AFTER_ASK.to_string(),
            image_quality: 85,
            audio_bitrate: "192k".to_string(),
            pdf_dpi: 144,
        }
    }
}

fn sanitize(settings: &mut Settings) {
    let valid_after = [AFTER_ASK, AFTER_OPEN_FOLDER, AFTER_NOTIFY];
    if !valid_after.contains(&settings.after_conversion.as_str()) {
        settings.after_conversion = AFTER_ASK.to_string();
    }
    settings.image_quality = settings.image_quality.clamp(10, 100);
    if settings.audio_bitrate.trim().is_empty() {
        settings.audio_bitrate = "192k".to_string();
    }
    if settings.pdf_dpi == 0 {
        settings.pdf_dpi = 144;
    }
}

/// Default output directory: `Documents/File Converter Pro`
/// (created on demand when a job starts, not here).
pub fn default_output_dir<R: Runtime>(app: &AppHandle<R>) -> PathBuf {
    app.path()
        .document_dir()
        .or_else(|_| app.path().home_dir().map(|home| home.join("Documents")))
        .map(|documents| documents.join("File Converter Pro"))
        .unwrap_or_else(|_| PathBuf::from("File Converter Pro"))
}

/// Load settings from the store, filling defaults and resolving an empty
/// `outputDir` to the default documents folder.
pub fn load<R: Runtime>(app: &AppHandle<R>) -> Result<Settings, String> {
    let store = app.store(STORE_FILE).map_err(|e| e.to_string())?;
    let mut settings = store
        .get(KEY)
        .and_then(|value| serde_json::from_value::<Settings>(value).ok())
        .unwrap_or_default();
    sanitize(&mut settings);
    if settings.output_dir.trim().is_empty() {
        settings.output_dir = default_output_dir(app).to_string_lossy().into_owned();
    }
    Ok(settings)
}

/// Persist settings (sanitized) to the store.
pub fn save<R: Runtime>(app: &AppHandle<R>, settings: &Settings) -> Result<(), String> {
    let mut settings = settings.clone();
    sanitize(&mut settings);
    let store = app.store(STORE_FILE).map_err(|e| e.to_string())?;
    let value = serde_json::to_value(&settings).map_err(|e| e.to_string())?;
    store.set(KEY, value);
    store.save().map_err(|e| e.to_string())
}

/// One-time initialization: when the store has no settings yet, import v2's
/// `~/.file-converter-pro/settings.json` and `history.json` if present
/// (mapping `output_dir`/`audio_bitrate`/`image_quality`/`after_conversion`;
/// `last_ui`/`theme` are dropped), then persist the result.
pub fn init<R: Runtime>(app: &AppHandle<R>) {
    let Ok(store) = app.store(STORE_FILE) else {
        return;
    };
    if store.has(KEY) {
        return;
    }

    let mut settings = Settings::default();
    if let Ok(home) = app.path().home_dir() {
        let v2_dir = home.join(".file-converter-pro");
        if let Ok(text) = fs::read_to_string(v2_dir.join("settings.json")) {
            if let Ok(value) = serde_json::from_str::<Value>(&text) {
                settings = settings_from_v2(&value);
            }
        }
        history::import_v2(app, &v2_dir.join("history.json"));
    }

    if let Ok(value) = serde_json::to_value(&settings) {
        store.set(KEY, value);
        let _ = store.save();
    }
}

/// Map a v2 settings JSON object onto v3 settings.
/// `last_ui` and `theme` are intentionally dropped; `pdfDpi` is new in v3.
pub(crate) fn settings_from_v2(v2: &Value) -> Settings {
    let mut settings = Settings::default();
    if let Some(dir) = v2.get("output_dir").and_then(Value::as_str) {
        settings.output_dir = dir.trim().to_string();
    }
    if let Some(after) = v2.get("after_conversion").and_then(Value::as_str) {
        settings.after_conversion = after.to_string();
    }
    if let Some(quality) = v2.get("image_quality").and_then(Value::as_u64) {
        settings.image_quality = quality.min(u8::MAX as u64) as u8;
    }
    if let Some(bitrate) = v2.get("audio_bitrate").and_then(Value::as_str) {
        settings.audio_bitrate = bitrate.to_string();
    }
    sanitize(&mut settings);
    settings
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn serializes_camel_case() {
        let value = serde_json::to_value(Settings::default()).unwrap();
        let obj = value.as_object().unwrap();
        for key in [
            "outputDir",
            "afterConversion",
            "imageQuality",
            "audioBitrate",
            "pdfDpi",
        ] {
            assert!(obj.contains_key(key), "missing key {key}");
        }
        assert_eq!(obj.len(), 5);
    }

    #[test]
    fn defaults_match_contract() {
        let s = Settings::default();
        assert_eq!(s.after_conversion, "ask");
        assert_eq!(s.image_quality, 85);
        assert_eq!(s.audio_bitrate, "192k");
        assert_eq!(s.pdf_dpi, 144);
        assert!(s.output_dir.is_empty());
    }

    #[test]
    fn v2_import_maps_fields_and_drops_ui_keys() {
        let v2 = json!({
            "output_dir": "C:/Out",
            "after_conversion": "open_folder",
            "audio_bitrate": "320k",
            "image_quality": 70,
            "last_ui": "advanced",
            "theme": "dark"
        });
        let s = settings_from_v2(&v2);
        assert_eq!(s.output_dir, "C:/Out");
        assert_eq!(s.after_conversion, "open_folder");
        assert_eq!(s.audio_bitrate, "320k");
        assert_eq!(s.image_quality, 70);
        assert_eq!(s.pdf_dpi, 144); // new in v3, default
        let value = serde_json::to_value(&s).unwrap();
        assert!(value.get("lastUi").is_none());
        assert!(value.get("theme").is_none());
    }

    #[test]
    fn v2_import_sanitizes_bad_values() {
        let v2 = json!({
            "after_conversion": "explode",
            "image_quality": 3,
            "audio_bitrate": ""
        });
        let s = settings_from_v2(&v2);
        assert_eq!(s.after_conversion, "ask");
        assert_eq!(s.image_quality, 10);
        assert_eq!(s.audio_bitrate, "192k");
    }

    #[test]
    fn partial_json_deserializes_with_defaults() {
        let s: Settings = serde_json::from_value(json!({ "imageQuality": 55 })).unwrap();
        assert_eq!(s.image_quality, 55);
        assert_eq!(s.audio_bitrate, "192k");
        assert_eq!(s.pdf_dpi, 144);
    }
}
