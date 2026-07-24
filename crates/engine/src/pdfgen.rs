//! Raster image → PDF via printpdf 0.12.4: A4 portrait, 36pt margins,
//! aspect-fit centered. Receives every raster source including heic
//! (reuses images' ffmpeg-assisted decode).
//!
//! DCT pass-through note: this printpdf build ships without its `images`
//! feature (default features only), so raw JPEG streams cannot be embedded
//! as-is; pixels are embedded via the lossless FlateDecode path instead.

use std::fs;
use std::path::PathBuf;

use printpdf::{
    Mm, Op, PdfDocument, PdfPage, PdfSaveOptions, Pt, RawImage, RawImageData, RawImageFormat,
    XObjectTransform,
};

use crate::convert::ConversionRequest;
use crate::error::ConvertError;
use crate::images;
use crate::job::{CancelToken, ProgressFn};
use crate::options::Sidecars;

const A4_WIDTH_MM: f32 = 210.0;
const A4_HEIGHT_MM: f32 = 297.0;
const A4_WIDTH_PT: f32 = 595.275_6;
const A4_HEIGHT_PT: f32 = 841.889_8;
const MARGIN_PT: f32 = 36.0;

pub fn convert(
    req: &ConversionRequest,
    sidecars: &Sidecars,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    progress(5, "Reading image");
    let source = images::canonical_source_ext(&req.input);
    let img = images::decode_source(&req.input, &source, sidecars, cancel)?;
    cancel.check()?;
    progress(25, "Image decoded");

    let out = images::prepare_output_path(req, "pdf")?;
    let stem = req
        .input
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("image");

    progress(60, "Building PDF");
    // v2 parity: composite alpha over white; PDF page background is white.
    let rgb = images::composite_white(&img);
    let (width_px, height_px) = rgb.dimensions();
    let raw = RawImage {
        pixels: RawImageData::U8(rgb.into_raw()),
        width: width_px as usize,
        height: height_px as usize,
        data_format: RawImageFormat::RGB8,
        tag: Vec::new(),
    };

    let mut doc = PdfDocument::new(stem);
    let image_id = doc.add_image(&raw);

    // Aspect-fit into the A4 content box, centered. dpi=72 makes the
    // XObject's base size exactly width_px x height_px in points.
    let content_w = A4_WIDTH_PT - 2.0 * MARGIN_PT;
    let content_h = A4_HEIGHT_PT - 2.0 * MARGIN_PT;
    let scale = (content_w / width_px as f32).min(content_h / height_px as f32);
    let draw_w = width_px as f32 * scale;
    let draw_h = height_px as f32 * scale;
    let transform = XObjectTransform {
        translate_x: Some(Pt(MARGIN_PT + (content_w - draw_w) / 2.0)),
        translate_y: Some(Pt(MARGIN_PT + (content_h - draw_h) / 2.0)),
        scale_x: Some(scale),
        scale_y: Some(scale),
        dpi: Some(72.0),
        ..XObjectTransform::default()
    };
    let page = PdfPage::new(
        Mm(A4_WIDTH_MM),
        Mm(A4_HEIGHT_MM),
        vec![Op::UseXobject {
            id: image_id,
            transform,
        }],
    );
    cancel.check()?;

    progress(90, "Writing PDF");
    let mut warnings = Vec::new();
    let bytes = doc
        .with_pages(vec![page])
        .save(&PdfSaveOptions::default(), &mut warnings);
    fs::write(&out, bytes)
        .map_err(|e| ConvertError::with_detail("Failed to write PDF output", e.to_string()))?;

    progress(100, "Done");
    Ok(vec![out])
}
