//! Raster image conversions: png/jpg/webp/bmp/tiff/gif/ico/heic → raster
//! targets + ico + gif (heic decoded via the ffmpeg sidecar first).
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
    Err(ConvertError::new("not implemented: images"))
}
