//! Document conversion tests (Task 7): pandoc matrix, typst PDF output,
//! txt→md in-process writer, and pdf→txt/md/html/docx/png/jpg via pdfium.
//!
//! Tests that need pandoc/typst/pdfium call `common::ensure_tools()` and skip
//! (early-return) when the tools cannot be located or downloaded.

mod common;

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use fcp_engine::convert::{convert, ConversionRequest};
use fcp_engine::error::ConvertError;
use fcp_engine::job::CancelToken;
use fcp_engine::options::{ConvertOptions, Sidecars};

fn run(
    input: &Path,
    target: &str,
    output_dir: &Path,
    sidecars: &Sidecars,
) -> Result<Vec<PathBuf>, ConvertError> {
    let req = ConversionRequest {
        input: input.to_path_buf(),
        target: target.to_string(),
        output_dir: output_dir.to_path_buf(),
        options: ConvertOptions::default(),
    };
    convert(&req, sidecars, &CancelToken::default(), &|_pct, _msg| {})
}

/// Compile a typst source file into a PDF fixture; panics on failure
/// (only called after `ensure_tools` succeeded, so typst is present).
fn typst_pdf(typst: &Path, dir: &Path, name: &str, source: &str) -> PathBuf {
    let typ = dir.join(format!("{name}.typ"));
    fs::write(&typ, source).unwrap();
    let pdf = dir.join(format!("{name}.pdf"));
    let status = Command::new(typst)
        .arg("compile")
        .arg(&typ)
        .arg(&pdf)
        .status()
        .expect("failed to spawn typst");
    assert!(status.success(), "typst compile failed");
    pdf
}

const ONE_PAGE_TYP: &str = "#set page(width: 300pt, height: 200pt)\n\
     Sovereign marker text for extraction tests.\n";

const TWO_PAGE_TYP: &str = "#set page(width: 300pt, height: 200pt)\n\
     Alpha page one marker\n\
     #pagebreak()\n\
     Beta page two marker\n";

// ---------------------------------------------------------------------------
// Ungated tests (no external tools required)
// ---------------------------------------------------------------------------

#[test]
fn txt_to_md_is_in_process_with_v2_escaping() {
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("notes.txt");
    fs::write(
        &input,
        "Stars *bold* and _under_ and `tick`\n\nSecond paragraph\n\n   \n",
    )
    .unwrap();

    let outs = run(&input, "md", dir.path(), &Sidecars::default()).unwrap();
    assert_eq!(outs.len(), 1);
    assert_eq!(outs[0].file_name().unwrap(), "notes_converted.md");

    let md = fs::read_to_string(&outs[0]).unwrap();
    assert!(md.starts_with("# notes\n\n"), "missing header: {md:?}");
    assert!(md.contains("\\*bold\\*"), "asterisk not escaped: {md:?}");
    assert!(md.contains("\\_under\\_"), "underscore not escaped: {md:?}");
    assert!(md.contains("\\`tick\\`"), "backtick not escaped: {md:?}");
    assert!(md.contains("Second paragraph"));
}

#[test]
fn pandoc_pair_without_pandoc_errors_clearly() {
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("a.md");
    fs::write(&input, "# Hi\n").unwrap();
    let err = run(&input, "html", dir.path(), &Sidecars::default()).unwrap_err();
    assert_eq!(err.message, "Pandoc is required for this conversion");
}

#[test]
fn pdf_render_without_pdfium_errors_clearly() {
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("a.pdf");
    fs::write(&input, "%PDF-1.4 not a real pdf").unwrap();
    let err = run(&input, "png", dir.path(), &Sidecars::default()).unwrap_err();
    assert_eq!(
        err.message,
        "PDF rendering requires the bundled pdfium library"
    );
}

// ---------------------------------------------------------------------------
// Gated tests (pandoc / typst / pdfium — skip when unavailable)
// ---------------------------------------------------------------------------

#[test]
fn md_to_html_contains_h1_and_is_standalone() {
    let Some(tools) = common::ensure_tools() else {
        eprintln!("skipping: tools unavailable");
        return;
    };
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("hello.md");
    fs::write(&input, "# Hello World\n\nSome body text.\n").unwrap();

    let outs = run(&input, "html", dir.path(), &tools).unwrap();
    assert_eq!(outs.len(), 1);
    assert_eq!(outs[0].file_name().unwrap(), "hello_converted.html");
    let html = fs::read_to_string(&outs[0]).unwrap();
    assert!(html.contains("<h1"), "no <h1 in output: {html}");
    assert!(html.contains("Hello World"));
    assert!(html.contains("<html"), "expected --standalone page: {html}");
}

#[test]
fn html_to_md_contains_hash_heading() {
    let Some(tools) = common::ensure_tools() else {
        eprintln!("skipping: tools unavailable");
        return;
    };
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("page.html");
    fs::write(
        &input,
        "<html><body><h1>Title Here</h1><p>para text</p></body></html>",
    )
    .unwrap();

    let outs = run(&input, "md", dir.path(), &tools).unwrap();
    let md = fs::read_to_string(&outs[0]).unwrap();
    assert!(md.contains('#'), "no hash heading in output: {md}");
    assert!(md.contains("Title Here"));
    assert!(md.contains("para text"));
}

#[test]
fn md_to_pdf_via_typst_produces_pdf_magic() {
    let Some(tools) = common::ensure_tools() else {
        eprintln!("skipping: tools unavailable");
        return;
    };
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("doc.md");
    fs::write(&input, "# Heading\n\nHello typst pdf output.\n").unwrap();

    let outs = run(&input, "pdf", dir.path(), &tools).unwrap();
    assert_eq!(outs.len(), 1);
    let bytes = fs::read(&outs[0]).unwrap();
    assert!(bytes.starts_with(b"%PDF"), "output is not a PDF");
}

#[test]
fn md_to_pdf_without_typst_errors_clearly() {
    let Some(tools) = common::ensure_tools() else {
        eprintln!("skipping: tools unavailable");
        return;
    };
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("doc.md");
    fs::write(&input, "# Heading\n").unwrap();

    let sidecars = Sidecars {
        typst: None,
        ..tools
    };
    let err = run(&input, "pdf", dir.path(), &sidecars).unwrap_err();
    assert_eq!(err.message, "Typst is required for PDF output");
}

#[test]
fn md_docx_txt_roundtrip_preserves_body_text() {
    let Some(tools) = common::ensure_tools() else {
        eprintln!("skipping: tools unavailable");
        return;
    };
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("story.md");
    fs::write(&input, "# Story\n\nquantum banana harvest\n").unwrap();

    let docx_outs = run(&input, "docx", dir.path(), &tools).unwrap();
    assert_eq!(docx_outs.len(), 1);
    let docx_bytes = fs::read(&docx_outs[0]).unwrap();
    assert!(docx_bytes.starts_with(b"PK"), "docx is not a zip archive");

    let txt_outs = run(&docx_outs[0], "txt", dir.path(), &tools).unwrap();
    let text = fs::read_to_string(&txt_outs[0]).unwrap();
    assert!(
        text.contains("quantum banana harvest"),
        "body text lost in roundtrip: {text}"
    );
}

#[test]
fn pdf_to_txt_contains_known_string() {
    let Some(tools) = common::ensure_tools() else {
        eprintln!("skipping: tools unavailable");
        return;
    };
    let dir = tempfile::tempdir().unwrap();
    let pdf = typst_pdf(
        tools.typst.as_ref().unwrap(),
        dir.path(),
        "hello",
        ONE_PAGE_TYP,
    );

    let outs = run(&pdf, "txt", dir.path(), &tools).unwrap();
    assert_eq!(outs[0].file_name().unwrap(), "hello_converted.txt");
    let text = fs::read_to_string(&outs[0]).unwrap();
    assert!(text.contains("Sovereign"), "known string missing: {text:?}");
}

#[test]
fn pdf_to_md_has_filename_hash_header() {
    let Some(tools) = common::ensure_tools() else {
        eprintln!("skipping: tools unavailable");
        return;
    };
    let dir = tempfile::tempdir().unwrap();
    let pdf = typst_pdf(
        tools.typst.as_ref().unwrap(),
        dir.path(),
        "report",
        ONE_PAGE_TYP,
    );

    let outs = run(&pdf, "md", dir.path(), &tools).unwrap();
    let md = fs::read_to_string(&outs[0]).unwrap();
    assert!(md.starts_with("# report\n\n"), "missing header: {md:?}");
    assert!(md.contains("Sovereign"));
}

#[test]
fn pdf_to_html_uses_v2_boilerplate_page() {
    let Some(tools) = common::ensure_tools() else {
        eprintln!("skipping: tools unavailable");
        return;
    };
    let dir = tempfile::tempdir().unwrap();
    let pdf = typst_pdf(
        tools.typst.as_ref().unwrap(),
        dir.path(),
        "page",
        ONE_PAGE_TYP,
    );

    let outs = run(&pdf, "html", dir.path(), &tools).unwrap();
    let html = fs::read_to_string(&outs[0]).unwrap();
    assert!(html.contains("font-family:Arial"), "missing Arial: {html}");
    assert!(
        html.contains("max-width:800px"),
        "missing max-width: {html}"
    );
    assert!(
        html.contains("line-height:1.6"),
        "missing line-height: {html}"
    );
    assert!(html.contains("<p>"), "missing <p>: {html}");
    assert!(html.contains("Sovereign"));
}

#[test]
fn pdf_to_docx_via_pandoc_roundtrips_text() {
    let Some(tools) = common::ensure_tools() else {
        eprintln!("skipping: tools unavailable");
        return;
    };
    let dir = tempfile::tempdir().unwrap();
    let pdf = typst_pdf(
        tools.typst.as_ref().unwrap(),
        dir.path(),
        "memo",
        ONE_PAGE_TYP,
    );

    let outs = run(&pdf, "docx", dir.path(), &tools).unwrap();
    assert_eq!(outs.len(), 1);
    let bytes = fs::read(&outs[0]).unwrap();
    assert!(bytes.starts_with(b"PK"), "docx is not a zip archive");

    let txt_outs = run(&outs[0], "txt", dir.path(), &tools).unwrap();
    let text = fs::read_to_string(&txt_outs[0]).unwrap();
    assert!(text.contains("Sovereign"), "text lost: {text:?}");
}

#[test]
fn pdf_to_png_single_page_uses_normal_unique_name() {
    let Some(tools) = common::ensure_tools() else {
        eprintln!("skipping: tools unavailable");
        return;
    };
    let dir = tempfile::tempdir().unwrap();
    let pdf = typst_pdf(
        tools.typst.as_ref().unwrap(),
        dir.path(),
        "single",
        ONE_PAGE_TYP,
    );

    let outs = run(&pdf, "png", dir.path(), &tools).unwrap();
    assert_eq!(outs.len(), 1);
    assert_eq!(outs[0].file_name().unwrap(), "single_converted.png");
    let img = image::open(&outs[0]).unwrap();
    assert!(img.width() > 0 && img.height() > 0);
}

#[test]
fn pdf_to_png_multi_page_names_each_page() {
    let Some(tools) = common::ensure_tools() else {
        eprintln!("skipping: tools unavailable");
        return;
    };
    let dir = tempfile::tempdir().unwrap();
    let pdf = typst_pdf(
        tools.typst.as_ref().unwrap(),
        dir.path(),
        "multi",
        TWO_PAGE_TYP,
    );

    let outs = run(&pdf, "png", dir.path(), &tools).unwrap();
    assert_eq!(outs.len(), 2, "expected one file per page: {outs:?}");
    assert_eq!(outs[0].file_name().unwrap(), "multi_converted_page1.png");
    assert_eq!(outs[1].file_name().unwrap(), "multi_converted_page2.png");
    for out in &outs {
        let img = image::open(out).unwrap();
        assert!(img.width() > 0 && img.height() > 0);
    }
}

#[test]
fn pdf_to_jpg_renders_decodable_image() {
    let Some(tools) = common::ensure_tools() else {
        eprintln!("skipping: tools unavailable");
        return;
    };
    let dir = tempfile::tempdir().unwrap();
    let pdf = typst_pdf(
        tools.typst.as_ref().unwrap(),
        dir.path(),
        "photo",
        ONE_PAGE_TYP,
    );

    let outs = run(&pdf, "jpg", dir.path(), &tools).unwrap();
    assert_eq!(outs.len(), 1);
    assert_eq!(outs[0].file_name().unwrap(), "photo_converted.jpg");
    let img = image::open(&outs[0]).unwrap();
    assert!(img.width() > 0 && img.height() > 0);
}
