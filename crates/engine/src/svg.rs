//! SVG conversions: svg → png/jpg/webp via resvg (render at intrinsic
//! size, 512px fallback), svg → pdf via svg2pdf.
//!
//! NOTE: svg2pdf 0.13 bundles its own usvg (0.45); the pdf path uses that
//! re-export, while raster paths use resvg 0.47's usvg. The two trees are
//! not interchangeable.

use std::fs;
use std::path::PathBuf;

use crate::convert::ConversionRequest;
use crate::error::ConvertError;
use crate::images;
use crate::job::{CancelToken, ProgressFn};
use crate::options::Sidecars;
use crate::registry;

const FALLBACK_SIZE: u32 = 512;

pub fn convert(
    req: &ConversionRequest,
    _sidecars: &Sidecars,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    progress(5, "Reading SVG");
    let data = fs::read(&req.input)
        .map_err(|e| ConvertError::with_detail("Failed to read input file", e.to_string()))?;
    cancel.check()?;

    let target = registry::normalize_ext(&req.target).to_string();
    let out = images::prepare_output_path(req, &target)?;

    if target == "pdf" {
        convert_to_pdf(&data, &out, cancel, progress)?;
    } else {
        convert_to_raster(&data, &target, &out, req, cancel, progress)?;
    }
    progress(100, "Done");
    Ok(vec![out])
}

fn convert_to_pdf(
    data: &[u8],
    out: &std::path::Path,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<(), ConvertError> {
    progress(25, "Parsing SVG");
    let mut options = svg2pdf::usvg::Options::default();
    options.fontdb_mut().load_system_fonts();
    let tree = svg2pdf::usvg::Tree::from_data(data, &options)
        .map_err(|e| ConvertError::with_detail("Failed to parse SVG", e.to_string()))?;
    cancel.check()?;

    progress(60, "Converting to PDF");
    let pdf = svg2pdf::to_pdf(
        &tree,
        svg2pdf::ConversionOptions::default(),
        svg2pdf::PageOptions::default(),
    )
    .map_err(|e| ConvertError::with_detail("Failed to convert SVG to PDF", e.to_string()))?;
    cancel.check()?;

    progress(90, "Writing output");
    fs::write(out, pdf)
        .map_err(|e| ConvertError::with_detail("Failed to write PDF output", e.to_string()))
}

fn convert_to_raster(
    data: &[u8],
    target: &str,
    out: &std::path::Path,
    req: &ConversionRequest,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<(), ConvertError> {
    progress(25, "Parsing SVG");
    let mut options = resvg::usvg::Options::default();
    options.fontdb_mut().load_system_fonts();
    let tree = resvg::usvg::Tree::from_data(data, &options)
        .map_err(|e| ConvertError::with_detail("Failed to parse SVG", e.to_string()))?;
    cancel.check()?;

    progress(60, "Rendering SVG");
    let size = tree.size();
    let (mut width, mut height) = (size.width().ceil() as u32, size.height().ceil() as u32);
    if width == 0 || height == 0 {
        width = FALLBACK_SIZE;
        height = FALLBACK_SIZE;
    }
    let mut pixmap = resvg::tiny_skia::Pixmap::new(width, height)
        .ok_or_else(|| ConvertError::new("Failed to allocate SVG render surface"))?;
    let transform = resvg::tiny_skia::Transform::from_scale(
        width as f32 / size.width(),
        height as f32 / size.height(),
    );
    resvg::render(&tree, transform, &mut pixmap.as_mut());
    cancel.check()?;

    let png = pixmap
        .encode_png()
        .map_err(|e| ConvertError::with_detail("Failed to capture rendered SVG", e.to_string()))?;
    let img = image::load_from_memory(&png)
        .map_err(|e| ConvertError::with_detail("Failed to decode rendered SVG", e.to_string()))?;

    progress(90, &format!("Encoding {}", target.to_uppercase()));
    images::encode_to_target(&img, target, out, &req.options, cancel)
}
