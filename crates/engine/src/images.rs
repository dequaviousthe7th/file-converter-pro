//! Raster image conversions: png/jpg/webp/bmp/tiff/gif/ico/heic → raster
//! targets + ico + gif (heic decoded via the ffmpeg sidecar first).
//!
//! Encoding per the plan's media parameters: JPEG at
//! `options.image_quality`, WebP lossy at the same quality, TIFF LZW,
//! PNG default, GIF first-frame for animated inputs, ICO multi-size
//! [16..256] via ico-builder fed with fast_image_resize downscales,
//! alpha composited over white for jpg/bmp targets, EXIF orientation
//! applied on decode for jpg/tiff.

use std::collections::HashMap;
use std::fs;
use std::io::BufWriter;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use image::codecs::jpeg::JpegEncoder;
use image::{DynamicImage, GenericImageView, ImageFormat, RgbImage, RgbaImage};

use crate::convert::{unique_output_path, ConversionRequest};
use crate::error::ConvertError;
use crate::job::{CancelToken, ProgressFn};
use crate::options::{ConvertOptions, Sidecars};
use crate::registry;

pub fn convert(
    req: &ConversionRequest,
    sidecars: &Sidecars,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    progress(5, "Reading image");
    let source = canonical_source_ext(&req.input);
    let img = decode_source(&req.input, &source, sidecars, cancel)?;
    cancel.check()?;
    progress(25, "Image decoded");

    let target = registry::normalize_ext(&req.target).to_string();
    let out = prepare_output_path(req, &target)?;

    progress(60, &format!("Encoding {}", target.to_uppercase()));
    encode_to_target(&img, &target, &out, &req.options, cancel)?;
    progress(90, "Finalizing");
    progress(100, "Done");
    Ok(vec![out])
}

/// Canonical (registry-normalized) extension of the input file.
pub(crate) fn canonical_source_ext(input: &Path) -> String {
    let raw = input.extension().and_then(|e| e.to_str()).unwrap_or("");
    registry::normalize_ext(raw).to_string()
}

/// Create the output dir if needed and return the collision-free output path.
pub(crate) fn prepare_output_path(
    req: &ConversionRequest,
    target: &str,
) -> Result<PathBuf, ConvertError> {
    let stem = req
        .input
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("output");
    fs::create_dir_all(&req.output_dir).map_err(|e| {
        ConvertError::with_detail("Failed to create output directory", e.to_string())
    })?;
    Ok(unique_output_path(&req.output_dir, stem, target))
}

/// Decode any raster source to a `DynamicImage`. HEIC goes through the
/// ffmpeg sidecar; jpg/tiff get their EXIF orientation applied.
pub(crate) fn decode_source(
    input: &Path,
    source: &str,
    sidecars: &Sidecars,
    cancel: &CancelToken,
) -> Result<DynamicImage, ConvertError> {
    if source == "heic" {
        return decode_heic(input, sidecars, cancel);
    }
    let bytes = fs::read(input)
        .map_err(|e| ConvertError::with_detail("Failed to read input file", e.to_string()))?;
    let img = image::load_from_memory(&bytes)
        .map_err(|e| ConvertError::with_detail("Failed to decode image", e.to_string()))?;
    if matches!(source, "jpg" | "tiff") {
        if let Some(orientation) = exif_orientation(&bytes) {
            return Ok(apply_orientation(img, orientation));
        }
    }
    Ok(img)
}

fn decode_heic(
    input: &Path,
    sidecars: &Sidecars,
    cancel: &CancelToken,
) -> Result<DynamicImage, ConvertError> {
    let ffmpeg = sidecars
        .ffmpeg
        .as_deref()
        .ok_or_else(|| ConvertError::new("HEIC support requires the bundled ffmpeg (not found)"))?;
    cancel.check()?;

    let tmp = tempfile::tempdir()
        .map_err(|e| ConvertError::with_detail("Failed to create temp directory", e.to_string()))?;
    let frame = tmp.path().join("frame.png");

    let mut cmd = Command::new(ffmpeg);
    cmd.arg("-y")
        .arg("-i")
        .arg(input)
        .args(["-frames:v", "1"])
        .arg(&frame)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
    }
    let output = cmd
        .output()
        .map_err(|e| ConvertError::with_detail("Failed to launch ffmpeg", e.to_string()))?;
    cancel.check()?;

    if !output.status.success() || !frame.exists() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let tail: String = stderr
            .chars()
            .rev()
            .take(1000)
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
            .collect();
        return Err(ConvertError::with_detail(
            "Failed to decode HEIC image",
            tail.trim().to_string(),
        ));
    }
    image::open(&frame)
        .map_err(|e| ConvertError::with_detail("Failed to decode image", e.to_string()))
}

fn exif_orientation(bytes: &[u8]) -> Option<u32> {
    let exif = exif::Reader::new()
        .read_from_container(&mut std::io::Cursor::new(bytes))
        .ok()?;
    exif.get_field(exif::Tag::Orientation, exif::In::PRIMARY)?
        .value
        .get_uint(0)
}

fn apply_orientation(img: DynamicImage, orientation: u32) -> DynamicImage {
    match orientation {
        2 => img.fliph(),
        3 => img.rotate180(),
        4 => img.flipv(),
        5 => img.rotate90().fliph(),
        6 => img.rotate90(),
        7 => img.rotate270().fliph(),
        8 => img.rotate270(),
        _ => img,
    }
}

/// Composite over a white background, discarding alpha (v2 parity for
/// jpg/bmp/pdf targets).
pub(crate) fn composite_white(img: &DynamicImage) -> RgbImage {
    let rgba = img.to_rgba8();
    let mut rgb = RgbImage::new(rgba.width(), rgba.height());
    for (src, dst) in rgba.pixels().zip(rgb.pixels_mut()) {
        let a = u32::from(src[3]);
        for c in 0..3 {
            dst[c] = ((u32::from(src[c]) * a + 255 * (255 - a) + 127) / 255) as u8;
        }
    }
    rgb
}

/// Encode a decoded image to `target`, honoring the shared quality knob.
/// Reused by `svg.rs` after rasterization.
pub(crate) fn encode_to_target(
    img: &DynamicImage,
    target: &str,
    out: &Path,
    options: &ConvertOptions,
    cancel: &CancelToken,
) -> Result<(), ConvertError> {
    cancel.check()?;
    match target {
        "png" => save_as(img, out, ImageFormat::Png),
        "jpg" => encode_jpeg(img, out, options.image_quality),
        "bmp" => save_as(
            &DynamicImage::ImageRgb8(composite_white(img)),
            out,
            ImageFormat::Bmp,
        ),
        "webp" => encode_webp(img, out, options.image_quality),
        "tiff" => encode_tiff_lzw(img, out),
        "gif" => save_as(
            &DynamicImage::ImageRgba8(img.to_rgba8()),
            out,
            ImageFormat::Gif,
        ),
        "ico" => encode_ico(img, out, cancel),
        other => Err(ConvertError::new(format!(
            "Unsupported image target: {other}"
        ))),
    }
}

fn save_as(img: &DynamicImage, out: &Path, format: ImageFormat) -> Result<(), ConvertError> {
    img.save_with_format(out, format).map_err(|e| {
        ConvertError::with_detail(format!("Failed to encode {format:?} output"), e.to_string())
    })
}

fn encode_jpeg(img: &DynamicImage, out: &Path, quality: u8) -> Result<(), ConvertError> {
    let rgb = composite_white(img);
    let file = fs::File::create(out)
        .map_err(|e| ConvertError::with_detail("Failed to create output file", e.to_string()))?;
    let mut writer = BufWriter::new(file);
    let mut encoder = JpegEncoder::new_with_quality(&mut writer, quality.clamp(1, 100));
    encoder
        .encode_image(&rgb)
        .map_err(|e| ConvertError::with_detail("Failed to encode JPEG output", e.to_string()))
}

fn encode_webp(img: &DynamicImage, out: &Path, quality: u8) -> Result<(), ConvertError> {
    let rgba = img.to_rgba8();
    let encoder = webp::Encoder::from_rgba(&rgba, rgba.width(), rgba.height());
    let memory = encoder.encode(f32::from(quality.clamp(1, 100)));
    fs::write(out, &*memory)
        .map_err(|e| ConvertError::with_detail("Failed to write WebP output", e.to_string()))
}

const ICO_SIZES: [u32; 7] = [16, 24, 32, 48, 64, 128, 256];

fn encode_ico(img: &DynamicImage, out: &Path, cancel: &CancelToken) -> Result<(), ConvertError> {
    use fast_image_resize as fr;

    let rgba = img.to_rgba8();
    let (width, height) = rgba.dimensions();
    let src = fr::images::Image::from_vec_u8(width, height, rgba.into_raw(), fr::PixelType::U8x4)
        .map_err(|e| {
        ConvertError::with_detail("Failed to prepare ICO source", e.to_string())
    })?;

    let tmp = tempfile::tempdir()
        .map_err(|e| ConvertError::with_detail("Failed to create temp directory", e.to_string()))?;
    let mut resizer = fr::Resizer::new();
    let mut sources = Vec::with_capacity(ICO_SIZES.len());
    for &size in &ICO_SIZES {
        cancel.check()?;
        let mut dst = fr::images::Image::new(size, size, fr::PixelType::U8x4);
        resizer
            .resize(&src, &mut dst, None)
            .map_err(|e| ConvertError::with_detail("Failed to resize ICO layer", e.to_string()))?;
        let layer = RgbaImage::from_raw(size, size, dst.into_vec())
            .ok_or_else(|| ConvertError::new("Failed to build ICO layer buffer"))?;
        let path = tmp.path().join(format!("icon-{size}.png"));
        layer
            .save_with_format(&path, ImageFormat::Png)
            .map_err(|e| ConvertError::with_detail("Failed to write ICO layer", e.to_string()))?;
        sources.push(path);
    }

    let mut builder = ico_builder::IcoBuilder::default();
    builder.sizes(&ICO_SIZES[..]);
    builder.add_source_files(&sources);
    builder
        .build_file(out)
        .map_err(|e| ConvertError::with_detail("Failed to encode ICO output", e.to_string()))
}

// --- TIFF LZW writer -------------------------------------------------------
//
// The image crate's TiffEncoder cannot enable compression (and the `tiff`
// crate is not a direct dependency), so the v2-parity "TIFF LZW" requirement
// is met with a minimal baseline-TIFF writer: single strip, chunky RGB(A),
// classic TIFF6 LZW with early code-size change (libtiff-compatible; the
// roundtrip is verified against the image/tiff decoder in tests).

fn encode_tiff_lzw(img: &DynamicImage, out: &Path) -> Result<(), ConvertError> {
    let (width, height) = img.dimensions();
    let (pixels, samples_per_pixel) = if img.color().has_alpha() {
        (img.to_rgba8().into_raw(), 4u16)
    } else {
        (img.to_rgb8().into_raw(), 3u16)
    };
    let strip = lzw_compress_tiff(&pixels);
    let bytes = build_tiff(width, height, samples_per_pixel, &strip);
    fs::write(out, bytes)
        .map_err(|e| ConvertError::with_detail("Failed to write TIFF output", e.to_string()))
}

fn build_tiff(width: u32, height: u32, spp: u16, strip: &[u8]) -> Vec<u8> {
    const T_SHORT: u16 = 3;
    const T_LONG: u16 = 4;
    let has_alpha = spp == 4;

    let strip_offset = 8u32;
    let strip_padded = strip.len() + (strip.len() & 1); // keep offsets even
    let bps_offset = strip_offset + strip_padded as u32;
    let bps_len = u32::from(spp) * 2;
    let ifd_offset = bps_offset + bps_len;

    let mut out = Vec::with_capacity(8 + strip_padded + bps_len as usize + 200);
    out.extend_from_slice(b"II");
    out.extend_from_slice(&42u16.to_le_bytes());
    out.extend_from_slice(&ifd_offset.to_le_bytes());
    out.extend_from_slice(strip);
    if strip.len() & 1 == 1 {
        out.push(0);
    }
    for _ in 0..spp {
        out.extend_from_slice(&8u16.to_le_bytes()); // BitsPerSample values
    }

    let entry = |out: &mut Vec<u8>, tag: u16, kind: u16, count: u32, value: u32| {
        out.extend_from_slice(&tag.to_le_bytes());
        out.extend_from_slice(&kind.to_le_bytes());
        out.extend_from_slice(&count.to_le_bytes());
        if kind == T_SHORT && count == 1 {
            out.extend_from_slice(&(value as u16).to_le_bytes());
            out.extend_from_slice(&0u16.to_le_bytes());
        } else {
            out.extend_from_slice(&value.to_le_bytes());
        }
    };

    let n_entries: u16 = if has_alpha { 11 } else { 10 };
    out.extend_from_slice(&n_entries.to_le_bytes());
    entry(&mut out, 256, T_LONG, 1, width); // ImageWidth
    entry(&mut out, 257, T_LONG, 1, height); // ImageLength
    entry(&mut out, 258, T_SHORT, u32::from(spp), bps_offset); // BitsPerSample
    entry(&mut out, 259, T_SHORT, 1, 5); // Compression = LZW
    entry(&mut out, 262, T_SHORT, 1, 2); // Photometric = RGB
    entry(&mut out, 273, T_LONG, 1, strip_offset); // StripOffsets
    entry(&mut out, 277, T_SHORT, 1, u32::from(spp)); // SamplesPerPixel
    entry(&mut out, 278, T_LONG, 1, height); // RowsPerStrip
    entry(&mut out, 279, T_LONG, 1, strip.len() as u32); // StripByteCounts
    entry(&mut out, 284, T_SHORT, 1, 1); // PlanarConfiguration = chunky
    if has_alpha {
        entry(&mut out, 338, T_SHORT, 1, 2); // ExtraSamples = unassociated
    }
    out.extend_from_slice(&0u32.to_le_bytes()); // no next IFD
    out
}

struct BitWriter {
    out: Vec<u8>,
    acc: u32,
    nbits: u32,
}

impl BitWriter {
    fn put(&mut self, code: u16, width: u32) {
        self.acc = (self.acc << width) | u32::from(code);
        self.nbits += width;
        while self.nbits >= 8 {
            self.nbits -= 8;
            self.out.push((self.acc >> self.nbits) as u8);
        }
        self.acc &= (1 << self.nbits) - 1;
    }

    fn finish(mut self) -> Vec<u8> {
        if self.nbits > 0 {
            self.out.push((self.acc << (8 - self.nbits)) as u8);
        }
        self.out
    }
}

/// TIFF6 LZW with early code-size change: widths bump when the next free
/// code reaches 511/1023/2047, table resets via ClearCode at 4094.
fn lzw_compress_tiff(data: &[u8]) -> Vec<u8> {
    const CLEAR: u16 = 256;
    const EOI: u16 = 257;
    const FIRST_FREE: u16 = 258;
    const CLEAR_AT: u16 = 4094;

    // Emit width for the next code given the table's next free slot. The
    // tiff/weezl decoder bumps its read width right after deriving entry
    // 2^w - 2, so the first 10-bit code is written once next_code reaches
    // 512 (then 1024, 2048); before EOI the decoder derives one extra
    // entry, hence the `next_code + 1` at the flush site below.
    fn width_for(next_code: u16) -> u32 {
        match next_code {
            0..=511 => 9,
            512..=1023 => 10,
            1024..=2047 => 11,
            _ => 12,
        }
    }

    let mut bw = BitWriter {
        out: Vec::with_capacity(data.len() / 2 + 16),
        acc: 0,
        nbits: 0,
    };
    let mut width = 9u32;
    bw.put(CLEAR, width);

    let mut iter = data.iter().copied();
    let Some(first) = iter.next() else {
        bw.put(EOI, width);
        return bw.finish();
    };

    let mut table: HashMap<(u16, u8), u16> = HashMap::new();
    let mut next_code = FIRST_FREE;
    let mut omega = u16::from(first);
    for k in iter {
        if let Some(&code) = table.get(&(omega, k)) {
            omega = code;
            continue;
        }
        bw.put(omega, width);
        table.insert((omega, k), next_code);
        next_code += 1;
        width = width_for(next_code);
        omega = u16::from(k);
        if next_code == CLEAR_AT {
            bw.put(CLEAR, width);
            table.clear();
            next_code = FIRST_FREE;
            width = 9;
        }
    }
    bw.put(omega, width);
    // The decoder derives one more table entry from the final data code and
    // may bump its width before reading EOI; mirror that.
    width = width_for(next_code + 1);
    bw.put(EOI, width);
    bw.finish()
}
