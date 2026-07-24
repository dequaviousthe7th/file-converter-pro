//! Audio + video conversions via the ffmpeg sidecar (all audio pairs, all
//! video pairs, video → gif two-pass palette).
//! Implemented in Task 6 — that agent replaces ONLY this file (and sidecar.rs).
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
    Err(ConvertError::new("not implemented: media"))
}
