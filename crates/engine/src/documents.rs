//! Document conversions: md/html/docx/rtf/epub/txt matrix via pandoc,
//! X → pdf via pandoc + typst, and pdf → txt/md/docx/html/png/jpg via
//! `crate::pdf` (pdfium / pdf-extract).
//! Implemented in Task 7 — that agent replaces ONLY this file (and pdf.rs).
//! The signature below is fixed: `convert::convert` dispatches to it.

use std::path::PathBuf;

use crate::convert::ConversionRequest;
use crate::error::ConvertError;
use crate::job::{CancelToken, ProgressFn};
use crate::options::Sidecars;

#[allow(unused_variables)]
pub fn convert(
    req: &ConversionRequest,
    sidecars: &Sidecars,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    Err(ConvertError::new("not implemented: documents"))
}
