//! PDF wrapper: pdfium binding (lazy, from `Sidecars::pdfium`), text
//! extraction with `pdf-extract` fallback, page rendering.
//! Implemented in Task 7 — that agent replaces ONLY this file (and
//! documents.rs, which is its only consumer).

use std::path::{Path, PathBuf};

use crate::error::ConvertError;
use crate::job::{CancelToken, ProgressFn};

/// Extract the text content of a PDF (pdfium when available, else pdf-extract).
#[allow(unused_variables)]
pub fn extract_text(pdf_path: &Path, pdfium: Option<&Path>) -> Result<String, ConvertError> {
    Err(ConvertError::new("not implemented: pdf"))
}

/// Render every page of a PDF to `target_ext` images at `dpi`, writing
/// unique-suffixed `{stem}_converted_page{N}.{ext}` files into `output_dir`.
#[allow(unused_variables)]
#[allow(clippy::too_many_arguments)]
pub fn render_pages(
    pdf_path: &Path,
    output_dir: &Path,
    stem: &str,
    target_ext: &str,
    dpi: u32,
    quality: u8,
    pdfium: Option<&Path>,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    Err(ConvertError::new("not implemented: pdf"))
}
