//! Raster image → PDF via printpdf (A4, 36pt margins, aspect-fit, JPEG
//! pass-through). Receives every raster source including heic (may reuse
//! images' ffmpeg-assisted decode helpers).
//! Implemented in Task 3 — that agent replaces ONLY this file.
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
    Err(ConvertError::new("not implemented: pdfgen"))
}
