//! Table conversions: csv/xlsx/tsv/json pairs + → html (csv, calamine,
//! rust_xlsxwriter, serde_json). Receives json → csv/xlsx/tsv via v2's
//! special JSON routing in `convert::convert`.
//! Implemented in Task 4 — that agent replaces ONLY this file.
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
    Err(ConvertError::new("not implemented: data"))
}
