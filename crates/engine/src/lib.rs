//! fcp-engine — the pure-Rust conversion engine for File Converter Pro.
//!
//! No Tauri/GTK dependencies: `cargo test -p fcp-engine` runs anywhere.
//! Public API per the shared contracts; domain modules are private behind
//! `convert::convert` dispatch.

pub mod convert; // dispatch entry point
pub mod error; // ConvertError
pub mod job; // CancelToken, ProgressFn
pub mod options; // ConvertOptions, Sidecars
pub mod registry; // format matrix

// Utility modules used by the domain implementations.
pub mod pdf; // pdfium wrapper (Task 7)
pub mod sidecar; // sidecar process runner (Task 6)

// Domain modules (private behind convert::dispatch). Each is implemented by
// exactly one later task, which replaces ONLY its own file(s) — never
// convert.rs, lib.rs, or Cargo.toml.
pub(crate) mod config; // json/yaml/toml trio (Task 5)
pub(crate) mod data; // csv/xlsx/tsv/json tables (Task 4)
pub(crate) mod documents; // pandoc/typst/pdfium documents (Task 7)
pub(crate) mod images; // raster images (Task 3)
pub(crate) mod media; // ffmpeg audio/video/gif (Task 6)
pub(crate) mod pdfgen; // image -> pdf (Task 3)
pub(crate) mod svg; // svg -> png/jpg/webp/pdf (Task 3)
