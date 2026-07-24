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
    assert!(
        err.message.contains("not implemented"),
        "unexpected message: {}",
        err.message
    );
}

#[test]
fn dispatch_routes_by_domain() {
    let dir = tempfile::tempdir().unwrap();
    let msg =
        |file: &str, target: &str| run(&request(dir.path(), file, target)).unwrap_err().message;

    // raster image -> raster target
    assert_eq!(msg("a.png", "jpg"), "not implemented: images");
    // alias source, alias-cased target
    assert_eq!(msg("b.JPEG", "PNG"), "not implemented: images");
    // heic goes through images (ffmpeg-assisted)
    assert_eq!(msg("c.heic", "png"), "not implemented: images");
    // raster image -> pdf goes to pdfgen
    assert_eq!(msg("d.png", "pdf"), "not implemented: pdfgen");
    // svg
    assert_eq!(msg("e.svg", "png"), "not implemented: svg");
    assert_eq!(msg("f.svg", "pdf"), "not implemented: svg");
    // audio + video
    assert_eq!(msg("g.mp3", "wav"), "not implemented: media");
    assert_eq!(msg("h.mp4", "gif"), "not implemented: media");
    // documents (including pdf -> image)
    assert_eq!(msg("i.md", "html"), "not implemented: documents");
    assert_eq!(msg("j.pdf", "png"), "not implemented: documents");
    assert_eq!(msg("k.epub", "docx"), "not implemented: documents");
    // data tables
    assert_eq!(msg("l.csv", "xlsx"), "not implemented: data");
    assert_eq!(msg("m.tsv", "json"), "not implemented: data");
    // v2 special JSON routing: json -> yaml/toml is config, json -> tables is data
    assert_eq!(msg("n.json", "yaml"), "not implemented: config");
    assert_eq!(msg("o.json", "toml"), "not implemented: config");
    assert_eq!(msg("p.json", "csv"), "not implemented: data");
    assert_eq!(msg("q.json", "xlsx"), "not implemented: data");
    assert_eq!(msg("r.json", "tsv"), "not implemented: data");
    // config trio
    assert_eq!(msg("s.yaml", "json"), "not implemented: config");
    assert_eq!(msg("t.toml", "yaml"), "not implemented: config");
    // yml alias routes like yaml
    assert_eq!(msg("u.yml", "json"), "not implemented: config");
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
