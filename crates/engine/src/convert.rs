//! Conversion entry point: validates the request against the registry and
//! dispatches to the domain modules by `(normalized source ext, target)`.
//!
//! Routing (do not change — later agents implement the domain modules against
//! exactly this wiring):
//! - raster images (png jpg webp bmp tiff gif ico heic) → `images`,
//!   except `→ pdf` which goes to `pdfgen` (heic included; pdfgen may reuse
//!   images' ffmpeg-assisted decode helpers)
//! - svg → `svg` (png/jpg/webp/pdf)
//! - audio (mp3 wav flac ogg aac m4a wma) and video (mp4 avi mkv mov webm,
//!   incl. → gif) → `media`
//! - documents (pdf docx md txt html rtf epub) → `documents`
//!   (incl. pdf → txt/md/docx/html/png/jpg)
//! - tables (csv xlsx tsv) → `data`
//! - json → `config` for yaml/toml targets, `data` for csv/xlsx/tsv
//!   (v2's special JSON routing)
//! - yaml/toml → `config`

use std::path::{Path, PathBuf};

use crate::error::ConvertError;
use crate::job::{CancelToken, ProgressFn};
use crate::options::{ConvertOptions, Sidecars};
use crate::registry;
use crate::{config, data, documents, images, media, pdfgen, svg};

pub struct ConversionRequest {
    pub input: PathBuf,
    pub target: String,
    pub output_dir: PathBuf,
    pub options: ConvertOptions,
}

const RASTER_SOURCES: &[&str] = &["png", "jpg", "webp", "bmp", "tiff", "gif", "ico", "heic"];
const AUDIO_SOURCES: &[&str] = &["mp3", "wav", "flac", "ogg", "aac", "m4a", "wma"];
const VIDEO_SOURCES: &[&str] = &["mp4", "avi", "mkv", "mov", "webm"];
const DOCUMENT_SOURCES: &[&str] = &["pdf", "docx", "md", "txt", "html", "rtf", "epub"];
const TABLE_SOURCES: &[&str] = &["csv", "xlsx", "tsv"];
const CONFIG_SOURCES: &[&str] = &["yaml", "toml"];

/// Convert `req.input` to `req.target`, writing into `req.output_dir`.
///
/// Returns the produced output paths (usually 1; N for pdf→image pages).
pub fn convert(
    req: &ConversionRequest,
    sidecars: &Sidecars,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    let raw_ext = req
        .input
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or_default();
    if raw_ext.is_empty() {
        return Err(ConvertError::new("Input file has no extension"));
    }

    let format = registry::format_for(raw_ext).ok_or_else(|| {
        ConvertError::new(format!(
            ".{} files are not supported",
            raw_ext.to_ascii_lowercase()
        ))
    })?;
    let source = format.ext; // canonical
    let target = registry::normalize_ext(&req.target);

    if !format.targets.contains(&target) {
        return Err(ConvertError::new(format!(
            "Conversion {source} \u{2192} {target} is not supported"
        )));
    }

    if !req.input.exists() {
        return Err(ConvertError::new(format!(
            "Input file not found: {}",
            req.input.display()
        )));
    }

    cancel.check()?;

    if RASTER_SOURCES.contains(&source) {
        if target == "pdf" {
            pdfgen::convert(req, sidecars, cancel, progress)
        } else {
            images::convert(req, sidecars, cancel, progress)
        }
    } else if source == "svg" {
        svg::convert(req, sidecars, cancel, progress)
    } else if AUDIO_SOURCES.contains(&source) || VIDEO_SOURCES.contains(&source) {
        media::convert(req, sidecars, cancel, progress)
    } else if DOCUMENT_SOURCES.contains(&source) {
        documents::convert(req, sidecars, cancel, progress)
    } else if source == "json" {
        match target {
            "yaml" | "toml" => config::convert(req, sidecars, cancel, progress),
            _ => data::convert(req, sidecars, cancel, progress),
        }
    } else if TABLE_SOURCES.contains(&source) {
        data::convert(req, sidecars, cancel, progress)
    } else if CONFIG_SOURCES.contains(&source) {
        config::convert(req, sidecars, cancel, progress)
    } else {
        Err(ConvertError::new(format!(
            "Conversion {source} \u{2192} {target} is not supported"
        )))
    }
}

/// Collision-free output path: `{stem}_converted.{ext}`, then
/// `{stem}_converted (1).{ext}`, `{stem}_converted (2).{ext}`, ...
pub fn unique_output_path(output_dir: &Path, stem: &str, ext: &str) -> PathBuf {
    let mut candidate = output_dir.join(format!("{stem}_converted.{ext}"));
    let mut counter = 1u32;
    while candidate.exists() {
        candidate = output_dir.join(format!("{stem}_converted ({counter}).{ext}"));
        counter += 1;
    }
    candidate
}
