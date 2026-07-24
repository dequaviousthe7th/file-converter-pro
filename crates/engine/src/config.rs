//! Config trio conversions: json/yaml/toml via a `serde_json::Value` hub
//! (serde-saphyr + toml). Receives json → yaml/toml via v2's special JSON
//! routing in `convert::convert` (json → csv/xlsx/tsv goes to `data`).
//! Implemented in Task 5 — that agent replaces ONLY this file.
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
    Err(ConvertError::new("not implemented: config"))
}
