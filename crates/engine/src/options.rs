//! Conversion options and sidecar binary locations (shared contract).

use std::path::PathBuf;

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct ConvertOptions {
    pub image_quality: u8,
    pub audio_bitrate: String,
    pub pdf_dpi: u32,
}

impl Default for ConvertOptions {
    fn default() -> Self {
        Self {
            image_quality: 85,
            audio_bitrate: "192k".to_string(),
            pdf_dpi: 144,
        }
    }
}

#[derive(Clone, Default)]
pub struct Sidecars {
    pub ffmpeg: Option<PathBuf>,
    pub pandoc: Option<PathBuf>,
    pub typst: Option<PathBuf>,
    pub pdfium: Option<PathBuf>,
}
