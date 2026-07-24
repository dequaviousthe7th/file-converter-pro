//! Sidecar process runner: spawn with timeout, kill-on-cancel,
//! CREATE_NO_WINDOW on Windows, stdout+stderr capture.
//! Implemented in Task 6 — that agent replaces ONLY this file (and media.rs).

use std::ffi::OsString;
use std::path::Path;
use std::process::Output;
use std::time::Duration;

use crate::error::ConvertError;
use crate::job::CancelToken;

/// Run a sidecar binary to completion, streaming stderr/stdout lines to
/// `on_line`. Polls the child every ~100ms; kills + waits on cancel or
/// timeout (no orphaned processes).
#[allow(unused_variables)]
pub fn run(
    bin: &Path,
    args: &[OsString],
    cancel: &CancelToken,
    timeout: Duration,
    on_line: impl FnMut(&str),
) -> Result<Output, ConvertError> {
    Err(ConvertError::new("not implemented: sidecar"))
}
