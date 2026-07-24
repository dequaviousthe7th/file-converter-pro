//! Task 3 tests: raster images, svg, image->pdf, heic (ffmpeg-gated).
//!
//! Fixtures are generated in-test with the image crate: 4x4 RGBA PNG,
//! JPEG, BMP, 2-frame GIF, noise PNG, and a tiny SVG string.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::Mutex;

use fcp_engine::convert::{convert, ConversionRequest};
use fcp_engine::error::ConvertError;
use fcp_engine::job::CancelToken;
use fcp_engine::options::{ConvertOptions, Sidecars};
use image::{DynamicImage, GenericImageView, Rgba, RgbaImage};

const TINY_SVG: &str = "<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64'>\
<rect width='64' height='64' fill='#00d4aa'/></svg>";

fn request(input: PathBuf, target: &str, output_dir: &Path) -> ConversionRequest {
    ConversionRequest {
        input,
        target: target.to_string(),
        output_dir: output_dir.to_path_buf(),
        options: ConvertOptions::default(),
    }
}

fn run(req: &ConversionRequest) -> Result<Vec<PathBuf>, ConvertError> {
    run_with(req, &Sidecars::default())
}

fn run_with(req: &ConversionRequest, sidecars: &Sidecars) -> Result<Vec<PathBuf>, ConvertError> {
    let cancel = CancelToken::default();
    convert(req, sidecars, &cancel, &|_p, _m| {})
}

/// 4x4 fully-transparent red RGBA PNG (tests white compositing).
fn transparent_png(dir: &Path) -> PathBuf {
    let img = RgbaImage::from_pixel(4, 4, Rgba([255, 0, 0, 0]));
    let path = dir.join("transparent.png");
    img.save(&path).unwrap();
    path
}

/// 4x4 RGBA PNG with varied colors and alphas.
fn rgba_png(dir: &Path) -> PathBuf {
    let mut img = RgbaImage::new(4, 4);
    for (x, y, px) in img.enumerate_pixels_mut() {
        *px = Rgba([(x * 60) as u8, (y * 60) as u8, 200, 55 + (x * 50) as u8]);
    }
    let path = dir.join("rgba.png");
    img.save(&path).unwrap();
    path
}

/// Deterministic RGB noise PNG (LCG), big enough to exercise LZW/JPEG paths.
fn noise_png(dir: &Path, side: u32) -> PathBuf {
    let mut state = 0x2545_F491u32;
    let mut img = image::RgbImage::new(side, side);
    for px in img.pixels_mut() {
        for c in 0..3 {
            state = state.wrapping_mul(1_664_525).wrapping_add(1_013_904_223);
            px[c] = (state >> 24) as u8;
        }
    }
    let path = dir.join("noise.png");
    img.save(&path).unwrap();
    path
}

#[test]
fn png_to_jpg_composites_alpha_over_white_and_reports_progress() {
    let dir = tempfile::tempdir().unwrap();
    let req = request(transparent_png(dir.path()), "jpg", dir.path());
    let seen = Mutex::new(Vec::<u8>::new());
    let progress = |p: u8, _m: &str| seen.lock().unwrap().push(p);
    let outputs = convert(
        &req,
        &Sidecars::default(),
        &CancelToken::default(),
        &progress,
    )
    .unwrap();

    assert_eq!(outputs.len(), 1);
    assert_eq!(
        outputs[0].file_name().unwrap().to_str().unwrap(),
        "transparent_converted.jpg"
    );
    let out = image::open(&outputs[0]).unwrap();
    assert!(
        !out.color().has_alpha(),
        "jpg output must not have alpha, got {:?}",
        out.color()
    );
    assert_eq!(out.dimensions(), (4, 4));
    let px = out.to_rgb8().get_pixel(0, 0).0;
    assert!(
        px.iter().all(|&c| c >= 240),
        "transparent input must composite to white, got {px:?}"
    );

    let seen = seen.lock().unwrap();
    for expected in [5u8, 25, 60, 90, 100] {
        assert!(
            seen.contains(&expected),
            "progress must include {expected}, got {seen:?}"
        );
    }
    assert_eq!(*seen.last().unwrap(), 100);
}

#[test]
fn png_to_ico_contains_multi_sizes_including_256() {
    let dir = tempfile::tempdir().unwrap();
    let req = request(noise_png(dir.path(), 64), "ico", dir.path());
    let outputs = run(&req).unwrap();
    let bytes = fs::read(&outputs[0]).unwrap();

    // ICONDIR: reserved u16, type u16 (1 = icon), count u16.
    assert_eq!(u16::from_le_bytes([bytes[0], bytes[1]]), 0);
    assert_eq!(u16::from_le_bytes([bytes[2], bytes[3]]), 1);
    let count = u16::from_le_bytes([bytes[4], bytes[5]]) as usize;
    assert_eq!(count, 7, "expected 7 entries (16..256)");
    let widths: Vec<u8> = (0..count).map(|i| bytes[6 + i * 16]).collect();
    assert!(
        widths.contains(&0),
        "must contain a 256px entry (width byte 0), got {widths:?}"
    );
    assert!(widths.contains(&16), "must contain a 16px entry");
}

#[test]
fn jpg_quality_knob_changes_file_size() {
    let dir = tempfile::tempdir().unwrap();
    let input = noise_png(dir.path(), 128);

    let low_dir = dir.path().join("low");
    let high_dir = dir.path().join("high");
    let mut low = request(input.clone(), "jpg", &low_dir);
    low.options.image_quality = 10;
    let mut high = request(input, "jpg", &high_dir);
    high.options.image_quality = 95;

    let low_out = run(&low).unwrap();
    let high_out = run(&high).unwrap();
    let low_size = fs::metadata(&low_out[0]).unwrap().len();
    let high_size = fs::metadata(&high_out[0]).unwrap().len();
    assert!(
        low_size < high_size,
        "q=10 ({low_size} bytes) must be smaller than q=95 ({high_size} bytes)"
    );
}

#[test]
fn svg_to_png_renders_at_intrinsic_size() {
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("tiny.svg");
    fs::write(&input, TINY_SVG).unwrap();
    let outputs = run(&request(input, "png", dir.path())).unwrap();

    let out = image::open(&outputs[0]).unwrap();
    assert_eq!(out.dimensions(), (64, 64), "intrinsic svg size is 64x64");
    let px = out.to_rgba8().get_pixel(32, 32).0;
    assert!(
        px[0] <= 3 && px[1].abs_diff(0xd4) <= 3 && px[2].abs_diff(0xaa) <= 3,
        "center pixel should be #00d4aa, got {px:?}"
    );
}

#[test]
fn svg_to_pdf_produces_pdf() {
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("tiny.svg");
    fs::write(&input, TINY_SVG).unwrap();
    let outputs = run(&request(input, "pdf", dir.path())).unwrap();
    let bytes = fs::read(&outputs[0]).unwrap();
    assert!(bytes.starts_with(b"%PDF"), "output must be a PDF");
}

#[test]
fn png_to_pdf_produces_pdf() {
    let dir = tempfile::tempdir().unwrap();
    let outputs = run(&request(rgba_png(dir.path()), "pdf", dir.path())).unwrap();
    assert_eq!(
        outputs[0].file_name().unwrap().to_str().unwrap(),
        "rgba_converted.pdf"
    );
    let bytes = fs::read(&outputs[0]).unwrap();
    assert!(bytes.starts_with(b"%PDF"), "output must be a PDF");
    assert!(bytes.len() > 500, "PDF should embed the image");
}

#[test]
fn tiff_lzw_roundtrip_noise() {
    let dir = tempfile::tempdir().unwrap();
    let input = noise_png(dir.path(), 128);
    let original = image::open(&input).unwrap().to_rgb8();
    let outputs = run(&request(input, "tiff", dir.path())).unwrap();

    let bytes = fs::read(&outputs[0]).unwrap();
    assert_eq!(&bytes[0..2], b"II", "little-endian TIFF");
    let ifd = u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as usize;
    let n = u16::from_le_bytes(bytes[ifd..ifd + 2].try_into().unwrap()) as usize;
    let mut compression = None;
    for i in 0..n {
        let e = ifd + 2 + i * 12;
        let tag = u16::from_le_bytes(bytes[e..e + 2].try_into().unwrap());
        if tag == 259 {
            compression = Some(u16::from_le_bytes(bytes[e + 8..e + 10].try_into().unwrap()));
        }
    }
    assert_eq!(compression, Some(5), "TIFF must be LZW-compressed");

    let decoded = image::open(&outputs[0]).unwrap().to_rgb8();
    assert_eq!(decoded.dimensions(), original.dimensions());
    assert!(
        decoded.as_raw() == original.as_raw(),
        "LZW roundtrip must be lossless"
    );
}

#[test]
fn tiff_preserves_alpha() {
    let dir = tempfile::tempdir().unwrap();
    let input = rgba_png(dir.path());
    let original = image::open(&input).unwrap().to_rgba8();
    let outputs = run(&request(input, "tiff", dir.path())).unwrap();
    let decoded = image::open(&outputs[0]).unwrap();
    assert!(decoded.color().has_alpha(), "tiff should keep alpha");
    assert!(decoded.to_rgba8().as_raw() == original.as_raw());
}

#[test]
fn animated_gif_uses_first_frame() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("anim.gif");
    {
        let file = fs::File::create(&path).unwrap();
        let mut enc = image::codecs::gif::GifEncoder::new(file);
        let delay = image::Delay::from_numer_denom_ms(100, 1);
        let frames = vec![
            image::Frame::from_parts(
                RgbaImage::from_pixel(8, 8, Rgba([255, 0, 0, 255])),
                0,
                0,
                delay,
            ),
            image::Frame::from_parts(
                RgbaImage::from_pixel(8, 8, Rgba([0, 0, 255, 255])),
                0,
                0,
                delay,
            ),
        ];
        enc.encode_frames(frames).unwrap();
    }

    let outputs = run(&request(path, "png", dir.path())).unwrap();
    let out = image::open(&outputs[0]).unwrap();
    assert_eq!(out.dimensions(), (8, 8));
    let px = out.to_rgb8().get_pixel(4, 4).0;
    assert!(
        px[0] > 200 && px[2] < 80,
        "first frame is red, got {px:?} (blue means second frame was used)"
    );
}

#[test]
fn bmp_to_png_roundtrip() {
    let dir = tempfile::tempdir().unwrap();
    let bmp = dir.path().join("plain.bmp");
    let mut img = image::RgbImage::new(4, 4);
    for (x, y, px) in img.enumerate_pixels_mut() {
        *px = image::Rgb([(x * 50) as u8, (y * 50) as u8, 99]);
    }
    img.save(&bmp).unwrap();
    let outputs = run(&request(bmp, "png", dir.path())).unwrap();
    let out = image::open(&outputs[0]).unwrap().to_rgb8();
    assert!(out.as_raw() == img.as_raw(), "bmp->png must be lossless");
}

#[test]
fn png_to_webp_is_decodable() {
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("teal.png");
    RgbaImage::from_pixel(16, 16, Rgba([0, 212, 170, 255]))
        .save(&input)
        .unwrap();
    let outputs = run(&request(input, "webp", dir.path())).unwrap();
    let out = image::open(&outputs[0]).unwrap();
    assert_eq!(out.dimensions(), (16, 16));
    let px = out.to_rgba8().get_pixel(8, 8).0;
    assert!(
        px[0] <= 12 && px[1].abs_diff(212) <= 12 && px[2].abs_diff(170) <= 12,
        "webp should stay close to teal, got {px:?}"
    );
}

#[test]
fn jpg_exif_orientation_is_applied() {
    let dir = tempfile::tempdir().unwrap();
    // 2 wide x 4 tall; orientation 6 (rotate 90 CW) makes it 4 wide x 2 tall.
    let mut jpeg_bytes = Vec::new();
    {
        let img = image::RgbImage::from_pixel(2, 4, image::Rgb([10, 200, 30]));
        let mut cursor = std::io::Cursor::new(&mut jpeg_bytes);
        let mut enc = image::codecs::jpeg::JpegEncoder::new_with_quality(&mut cursor, 90);
        enc.encode_image(&img).unwrap();
    }
    // Minimal EXIF APP1 segment: II TIFF, one IFD entry, Orientation = 6.
    #[rustfmt::skip]
    let app1: [u8; 36] = [
        0xFF, 0xE1, 0x00, 0x22, b'E', b'x', b'i', b'f', 0x00, 0x00,
        b'I', b'I', 0x2A, 0x00, 0x08, 0x00, 0x00, 0x00, // TIFF header, IFD @8
        0x01, 0x00,                                     // 1 entry
        0x12, 0x01, 0x03, 0x00, 0x01, 0x00, 0x00, 0x00, // tag 0x0112 SHORT x1
        0x06, 0x00, 0x00, 0x00,                         // value 6
        0x00, 0x00, 0x00, 0x00,                         // no next IFD
    ];
    let mut with_exif = Vec::with_capacity(jpeg_bytes.len() + app1.len());
    with_exif.extend_from_slice(&jpeg_bytes[..2]); // SOI
    with_exif.extend_from_slice(&app1);
    with_exif.extend_from_slice(&jpeg_bytes[2..]);
    let input = dir.path().join("oriented.jpg");
    fs::write(&input, with_exif).unwrap();

    let outputs = run(&request(input, "png", dir.path())).unwrap();
    let out = image::open(&outputs[0]).unwrap();
    assert_eq!(
        out.dimensions(),
        (4, 2),
        "orientation 6 must rotate 2x4 into 4x2"
    );
}

#[test]
fn heic_without_ffmpeg_reports_clear_error() {
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("photo.heic");
    fs::write(&input, b"dummy").unwrap();
    let err = run(&request(input, "png", dir.path())).unwrap_err();
    assert_eq!(
        err.message,
        "HEIC support requires the bundled ffmpeg (not found)"
    );
}

/// Skips silently unless ffmpeg exists and can decode hevc + encode libx265.
#[test]
fn heic_to_png_via_ffmpeg_sidecar() {
    let Some(ffmpeg) = find_ffmpeg() else { return };
    let can = |kind: &str, name: &str| -> bool {
        Command::new(&ffmpeg)
            .args(["-hide_banner", kind])
            .output()
            .map(|o| String::from_utf8_lossy(&o.stdout).contains(name))
            .unwrap_or(false)
    };
    if !can("-decoders", " hevc ") || !can("-encoders", "libx265") {
        return;
    }

    let dir = tempfile::tempdir().unwrap();
    let src = noise_png(dir.path(), 64);
    let heic = dir.path().join("photo.heic");
    // ffmpeg <7.1 cannot mux real HEIF; an hevc still in an mp4 container
    // exercises the identical sidecar decode path (ffmpeg sniffs content).
    let status = Command::new(&ffmpeg)
        .arg("-y")
        .arg("-i")
        .arg(&src)
        .args([
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx265",
            "-frames:v",
            "1",
            "-f",
            "mp4",
        ])
        .arg(&heic)
        .output();
    match status {
        Ok(o) if o.status.success() && heic.exists() => {}
        _ => return, // encoder unusable here; skip silently
    }

    let sidecars = Sidecars {
        ffmpeg: Some(ffmpeg),
        ..Sidecars::default()
    };
    let outputs = run_with(&request(heic, "png", dir.path()), &sidecars).unwrap();
    let out = image::open(&outputs[0]).unwrap();
    assert_eq!(out.dimensions(), (64, 64));
    assert!(matches!(
        out,
        DynamicImage::ImageRgb8(_) | DynamicImage::ImageRgba8(_)
    ));
}

fn find_ffmpeg() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("FCP_FFMPEG") {
        let p = PathBuf::from(p);
        if p.exists() {
            return Some(p);
        }
    }
    let default = PathBuf::from("/usr/bin/ffmpeg");
    default.exists().then_some(default)
}
