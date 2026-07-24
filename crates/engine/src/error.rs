//! `ConvertError` — the single error type of the engine (shared contract).

#[derive(Debug, thiserror::Error)]
#[error("{message}")]
pub struct ConvertError {
    pub message: String,
    pub detail: Option<String>,
}

impl ConvertError {
    pub fn new(msg: impl Into<String>) -> Self {
        Self {
            message: msg.into(),
            detail: None,
        }
    }

    pub fn with_detail(msg: impl Into<String>, detail: impl Into<String>) -> Self {
        Self {
            message: msg.into(),
            detail: Some(detail.into()),
        }
    }
}
