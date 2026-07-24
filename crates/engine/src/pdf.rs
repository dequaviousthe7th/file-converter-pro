//! PDF wrapper: pdfium binding (lazy, from `Sidecars::pdfium`), per-page text
//! extraction with a `pdf-extract` fallback when pdfium is missing, and page
//! rendering to raster images at a caller-chosen DPI.

use std::path::{Path, PathBuf};
use std::sync::{Mutex, OnceLock};

use pdfium_render::prelude::*;

use crate::error::ConvertError;
use crate::job::{CancelToken, ProgressFn};

/// The lazily-bound pdfium instance. pdfium-render only allows binding the
/// library once per process, so the first successful bind is cached for the
/// process lifetime (the library path never changes within one app run).
static PDFIUM: OnceLock<Result<Pdfium, String>> = OnceLock::new();

/// Serializes whole document operations on top of pdfium-render's own
/// per-FFI-call locking.
static PDFIUM_LOCK: Mutex<()> = Mutex::new(());

/// Accept either the pdfium library file itself or the directory holding it.
fn library_path(pdfium: &Path) -> String {
    if pdfium.is_dir() {
        Pdfium::pdfium_platform_library_name_at_path(pdfium)
            .to_string_lossy()
            .into_owned()
    } else {
        pdfium.to_string_lossy().into_owned()
    }
}

/// Bind pdfium (first call only) and run `f` with the initialized instance
/// (process-serialized).
fn with_pdfium<T>(
    lib: &Path,
    f: impl FnOnce(&Pdfium) -> Result<T, ConvertError>,
) -> Result<T, ConvertError> {
    let _guard = PDFIUM_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let pdfium = PDFIUM
        .get_or_init(|| {
            Pdfium::bind_to_library(library_path(lib))
                .map(Pdfium::new)
                .map_err(|e| e.to_string())
        })
        .as_ref()
        .map_err(|e| ConvertError::with_detail("Failed to load the pdfium library", e.clone()))?;
    f(pdfium)
}

/// Extract the text of every page. Uses pdfium when a library path is
/// provided (one entry per page); otherwise falls back to the pure-Rust
/// `pdf-extract` crate (whole document as a single entry).
pub fn extract_text_pages(
    pdf_path: &Path,
    pdfium: Option<&Path>,
) -> Result<Vec<String>, ConvertError> {
    if let Some(lib) = pdfium {
        let extracted = with_pdfium(lib, |p| {
            let doc = p
                .load_pdf_from_file(pdf_path, None)
                .map_err(|e| ConvertError::with_detail("Failed to open PDF", e.to_string()))?;
            let mut pages = Vec::new();
            for page in doc.pages().iter() {
                let text = page
                    .text()
                    .map_err(|e| {
                        ConvertError::with_detail("Failed to extract text from PDF", e.to_string())
                    })?
                    .all();
                pages.push(text);
            }
            Ok(pages)
        });
        // Only fall back when the *library* could not be loaded; a broken
        // document is a real error either way.
        match extracted {
            Ok(pages) => return Ok(pages),
            Err(e) if e.message == "Failed to load the pdfium library" => {}
            Err(e) => return Err(e),
        }
    }
    let text = pdf_extract::extract_text(pdf_path)
        .map_err(|e| ConvertError::with_detail("Failed to extract text from PDF", e.to_string()))?;
    Ok(vec![text])
}

/// Extract the whole document text (pages joined with blank lines).
pub fn extract_text(pdf_path: &Path, pdfium: Option<&Path>) -> Result<String, ConvertError> {
    let pages = extract_text_pages(pdf_path, pdfium)?;
    Ok(pages
        .iter()
        .filter(|t| !t.is_empty())
        .map(String::as_str)
        .collect::<Vec<_>>()
        .join("\n\n"))
}

/// Render every page of a PDF to `target_ext` images at `dpi`.
///
/// Naming: a single-page document gets the normal unique name
/// (`{stem}_converted.{ext}`); multi-page documents get
/// `{stem}_converted_page{N}.{ext}`, each unique-suffixed. Returns all paths.
#[allow(clippy::too_many_arguments)]
pub fn render_pages(
    pdf_path: &Path,
    output_dir: &Path,
    stem: &str,
    target_ext: &str,
    dpi: u32,
    quality: u8,
    pdfium: Option<&Path>,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    let Some(lib) = pdfium else {
        return Err(ConvertError::new(
            "PDF rendering requires the bundled pdfium library",
        ));
    };

    with_pdfium(lib, |p| {
        let doc = p
            .load_pdf_from_file(pdf_path, None)
            .map_err(|e| ConvertError::with_detail("Failed to open PDF", e.to_string()))?;
        let total = doc.pages().len() as usize;
        if total == 0 {
            return Err(ConvertError::new("PDF has no pages"));
        }
        let config = PdfRenderConfig::new().scale_page_by_factor(dpi as f32 / 72.0);

        let mut outputs: Vec<PathBuf> = Vec::with_capacity(total);
        let render = |outputs: &mut Vec<PathBuf>| -> Result<(), ConvertError> {
            for (i, page) in doc.pages().iter().enumerate() {
                cancel.check()?;
                progress(
                    (10 + 85 * i / total) as u8,
                    &format!("Rendering page {} of {total}...", i + 1),
                );
                let bitmap = page.render_with_config(&config).map_err(|e| {
                    ConvertError::with_detail(
                        format!("Failed to render PDF page {}", i + 1),
                        e.to_string(),
                    )
                })?;
                let image = bitmap.as_image().map_err(|e| {
                    ConvertError::with_detail(
                        format!("Failed to decode rendered PDF page {}", i + 1),
                        e.to_string(),
                    )
                })?;
                let path = if total == 1 {
                    crate::convert::unique_output_path(output_dir, stem, target_ext)
                } else {
                    unique_page_path(output_dir, stem, i + 1, target_ext)
                };
                write_image(&image, &path, target_ext, quality)?;
                outputs.push(path);
            }
            Ok(())
        };

        if let Err(e) = render(&mut outputs) {
            for produced in &outputs {
                let _ = std::fs::remove_file(produced);
            }
            return Err(e);
        }
        Ok(outputs)
    })
}

/// Collision-free `{stem}_converted_page{n}.{ext}` (then ` (1)`, ` (2)`, ...).
fn unique_page_path(output_dir: &Path, stem: &str, page: usize, ext: &str) -> PathBuf {
    let base = format!("{stem}_converted_page{page}");
    let mut candidate = output_dir.join(format!("{base}.{ext}"));
    let mut counter = 1u32;
    while candidate.exists() {
        candidate = output_dir.join(format!("{base} ({counter}).{ext}"));
        counter += 1;
    }
    candidate
}

fn write_image(
    image: &image::DynamicImage,
    path: &Path,
    ext: &str,
    quality: u8,
) -> Result<(), ConvertError> {
    let result = if ext == "jpg" {
        let file = std::fs::File::create(path).map_err(|e| {
            ConvertError::with_detail("Failed to create output file", e.to_string())
        })?;
        let mut writer = std::io::BufWriter::new(file);
        let mut encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(&mut writer, quality);
        encoder.encode_image(&image.to_rgb8())
    } else {
        image.save(path)
    };
    result.map_err(|e| ConvertError::with_detail("Failed to write page image", e.to_string()))
}
