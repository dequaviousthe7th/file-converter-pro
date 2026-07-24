//! Cancellation and progress primitives (shared contract).

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use crate::error::ConvertError;

#[derive(Clone, Default)]
pub struct CancelToken(Arc<AtomicBool>);

impl CancelToken {
    pub fn cancel(&self) {
        self.0.store(true, Ordering::SeqCst);
    }

    pub fn is_cancelled(&self) -> bool {
        self.0.load(Ordering::SeqCst)
    }

    /// Returns `Err("Conversion cancelled")` if the token has been cancelled.
    pub fn check(&self) -> Result<(), ConvertError> {
        if self.is_cancelled() {
            Err(ConvertError::new("Conversion cancelled"))
        } else {
            Ok(())
        }
    }
}

/// Progress callback: `(percent 0-100, message)`.
pub type ProgressFn<'a> = &'a (dyn Fn(u8, &str) + Send + Sync);
