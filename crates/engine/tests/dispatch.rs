use std::fs;
use std::path::{Path, PathBuf};

use fcp_engine::convert::{convert, ConversionRequest};
use fcp_engine::job::CancelToken;
use fcp_engine::options::{ConvertOptions, Sidecars};

fn request(dir: &Path, file_name: &str, target: &str) -> ConversionRequest {
    let input: PathBuf = dir.join(file_name);
    fs::write(&input, b"dummy").unwrap();
    ConversionRequest {
        input,
        target: target.to_string(),
        output_dir: dir.to_path_buf(),
        options: ConvertOptions::default(),
    }
}

fn run(req: &ConversionRequest) -> Result<Vec<PathBuf>, fcp_engine::error::ConvertError> {
    let sidecars = Sidecars::default();
    let cancel = CancelToken::default();
    convert(req, &sidecars, &cancel, &|_pct, _msg| {})
}

#[test]
fn unsupported_source_extension_errors() {
    let dir = tempfile::tempdir().unwrap();
    let req = request(dir.path(), "input.xyz", "png");
    let err = run(&req).unwrap_err();
    assert!(
        err.message.contains("not supported"),
        "unexpected message: {}",
        err.message
    );
}

#[test]
fn unsupported_pair_errors() {
    let dir = tempfile::tempdir().unwrap();
    // png is a real source but png -> mp3 is not in the matrix
    let req = request(dir.path(), "input.png", "mp3");
    let err = run(&req).unwrap_err();
    assert!(
        err.message.contains("not supported"),
        "unexpected message: {}",
        err.message
    );
}

#[test]
fn stubbed_pair_reports_not_implemented() {
    let dir = tempfile::tempdir().unwrap();
    let req = request(dir.path(), "input.png", "jpg");
    let err = run(&req).unwrap_err();
    // images (Task 3) is implemented: dummy bytes now fail at decode time.
    assert!(
        err.message.contains("Failed to decode image"),
        "unexpected message: {}",
        err.message
    );
}

#[test]
fn dispatch_routes_by_domain() {
    let dir = tempfile::tempdir().unwrap();
    let msg =
        |file: &str, target: &str| run(&request(dir.path(), file, target)).unwrap_err().message;

    // raster image -> raster target (images is implemented: dummy bytes
    // fail at decode time)
    assert_eq!(msg("a.png", "jpg"), "Failed to decode image");
    // alias source, alias-cased target
    assert_eq!(msg("b.JPEG", "PNG"), "Failed to decode image");
    // heic goes through images (ffmpeg-assisted; no sidecar configured here)
    assert_eq!(
        msg("c.heic", "png"),
        "HEIC support requires the bundled ffmpeg (not found)"
    );
    // raster image -> pdf goes to pdfgen (same shared decode)
    assert_eq!(msg("d.png", "pdf"), "Failed to decode image");
    // svg (implemented: dummy bytes are not parseable SVG)
    assert_eq!(msg("e.svg", "png"), "Failed to parse SVG");
    assert_eq!(msg("f.svg", "pdf"), "Failed to parse SVG");
    // audio + video (media is implemented: without an ffmpeg sidecar it
    // reports the missing-ffmpeg error)
    assert_eq!(
        msg("g.mp3", "wav"),
        "Audio/video conversion requires the bundled ffmpeg"
    );
    assert_eq!(
        msg("h.mp4", "gif"),
        "Audio/video conversion requires the bundled ffmpeg"
    );
    // documents (implemented: without the pandoc/pdfium sidecars they report
    // the missing-tool errors; pdf -> image requires pdfium)
    assert_eq!(
        msg("i.md", "html"),
        "Pandoc is required for this conversion"
    );
    assert_eq!(
        msg("j.pdf", "png"),
        "PDF rendering requires the bundled pdfium library"
    );
    assert_eq!(
        msg("k.epub", "docx"),
        "Pandoc is required for this conversion"
    );
    // data tables (implemented: the dummy file parses as a header-only table)
    assert_eq!(msg("l.csv", "xlsx"), "No data rows found");
    assert_eq!(msg("m.tsv", "json"), "No data rows found");
    // v2 special JSON routing: json -> yaml/toml is config, json -> tables is data
    // (config is implemented: the "dummy" fixture is invalid JSON)
    assert_eq!(msg("n.json", "yaml"), "Failed to parse JSON input");
    assert_eq!(msg("o.json", "toml"), "Failed to parse JSON input");
    assert_eq!(msg("p.json", "csv"), "Invalid JSON input");
    assert_eq!(msg("q.json", "xlsx"), "Invalid JSON input");
    assert_eq!(msg("r.json", "tsv"), "Invalid JSON input");
    // config trio (implemented: "dummy" is a valid YAML scalar, invalid TOML)
    assert!(run(&request(dir.path(), "s.yaml", "json")).is_ok());
    assert_eq!(msg("t.toml", "yaml"), "Failed to parse TOML input");
    // yml alias routes like yaml
    assert!(run(&request(dir.path(), "u.yml", "json")).is_ok());
}

#[test]
fn cancelled_token_short_circuits() {
    let dir = tempfile::tempdir().unwrap();
    let req = request(dir.path(), "input.png", "jpg");
    let sidecars = Sidecars::default();
    let cancel = CancelToken::default();
    cancel.cancel();
    let err = convert(&req, &sidecars, &cancel, &|_pct, _msg| {}).unwrap_err();
    assert_eq!(err.message, "Conversion cancelled");
}
