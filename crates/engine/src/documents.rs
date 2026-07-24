//! Document conversions (Task 7):
//! - the md/html/docx/rtf/epub/txt matrix via the pandoc sidecar
//!   (`-t plain` for txt output, `--standalone` for html output),
//! - X → pdf via pandoc with `--pdf-engine=<typst>`,
//! - txt → md via a small in-process writer (v2 parity),
//! - pdf → txt/md/html/docx via `crate::pdf` text extraction
//!   (pdfium, `pdf-extract` fallback),
//! - pdf → png/jpg via pdfium page rendering at `options.pdf_dpi`.

use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Duration;

use crate::convert::{unique_output_path, ConversionRequest};
use crate::error::ConvertError;
use crate::job::{CancelToken, ProgressFn};
use crate::options::Sidecars;
use crate::{pdf, registry, sidecar};

const PANDOC_TIMEOUT: Duration = Duration::from_secs(120);
const PDF_ENGINE_TIMEOUT: Duration = Duration::from_secs(240);

pub fn convert(
    req: &ConversionRequest,
    sidecars: &Sidecars,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    let raw_ext = req
        .input
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or_default();
    let source = registry::format_for(raw_ext)
        .map(|f| f.ext)
        .unwrap_or_else(|| registry::normalize_ext(raw_ext));
    let target = registry::normalize_ext(&req.target).to_string();
    let stem = req
        .input
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("output")
        .to_string();

    fs::create_dir_all(&req.output_dir).map_err(|e| {
        ConvertError::with_detail("Failed to create output directory", e.to_string())
    })?;
    cancel.check()?;

    match (source, target.as_str()) {
        ("txt", "md") => txt_to_md(req, &stem, cancel, progress),
        ("pdf", "txt") => pdf_to_text(req, sidecars, &stem, false, cancel, progress),
        ("pdf", "md") => pdf_to_text(req, sidecars, &stem, true, cancel, progress),
        ("pdf", "html") => pdf_to_html(req, sidecars, &stem, cancel, progress),
        ("pdf", "docx") => pdf_to_docx(req, sidecars, &stem, cancel, progress),
        ("pdf", "png" | "jpg") => {
            progress(5, "Rendering PDF pages...");
            let outputs = pdf::render_pages(
                &req.input,
                &req.output_dir,
                &stem,
                &target,
                req.options.pdf_dpi,
                req.options.image_quality,
                sidecars.pdfium.as_deref(),
                cancel,
                progress,
            )?;
            progress(100, "Done");
            Ok(outputs)
        }
        _ => pandoc_convert(
            &req.input,
            &req.output_dir,
            &stem,
            &target,
            sidecars,
            cancel,
            progress,
        ),
    }
}

/// txt → md in-process (v2 parity): `# {filename}` header, then each
/// non-empty paragraph with `*`, `_` and `` ` `` backslash-escaped.
fn txt_to_md(
    req: &ConversionRequest,
    stem: &str,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    progress(20, "Converting to Markdown...");
    let bytes = fs::read(&req.input)
        .map_err(|e| ConvertError::with_detail("Failed to read text file", e.to_string()))?;
    let content = String::from_utf8_lossy(&bytes);
    cancel.check()?;

    let mut md = format!("# {stem}\n\n");
    for para in content.split("\n\n") {
        if !para.trim().is_empty() {
            let escaped = para
                .replace('*', "\\*")
                .replace('_', "\\_")
                .replace('`', "\\`");
            md.push_str(&escaped);
            md.push_str("\n\n");
        }
    }

    let output = unique_output_path(&req.output_dir, stem, "md");
    fs::write(&output, md)
        .map_err(|e| ConvertError::with_detail("Failed to write Markdown file", e.to_string()))?;
    progress(100, "Done");
    Ok(vec![output])
}

/// Extracted document text with empty pages dropped, joined by blank lines.
fn extracted_full_text(
    req: &ConversionRequest,
    sidecars: &Sidecars,
) -> Result<String, ConvertError> {
    pdf::extract_text(&req.input, sidecars.pdfium.as_deref())
}

/// v2-parity markdown form of extracted PDF text: `# {stem}` header + text,
/// with triple newlines collapsed.
fn markdown_from_extracted(stem: &str, full_text: &str) -> String {
    format!("# {stem}\n\n{full_text}").replace("\n\n\n", "\n\n")
}

fn pdf_to_text(
    req: &ConversionRequest,
    sidecars: &Sidecars,
    stem: &str,
    as_markdown: bool,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    progress(10, "Extracting text from PDF...");
    let full_text = extracted_full_text(req, sidecars)?;
    cancel.check()?;

    let (content, ext) = if as_markdown {
        (markdown_from_extracted(stem, &full_text), "md")
    } else {
        (full_text, "txt")
    };

    let output = unique_output_path(&req.output_dir, stem, ext);
    fs::write(&output, content)
        .map_err(|e| ConvertError::with_detail("Failed to write output file", e.to_string()))?;
    progress(100, "Done");
    Ok(vec![output])
}

fn pdf_to_html(
    req: &ConversionRequest,
    sidecars: &Sidecars,
    stem: &str,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    progress(10, "Extracting text from PDF...");
    let pages = pdf::extract_text_pages(&req.input, sidecars.pdfium.as_deref())?;
    let total = pages.len().max(1);

    let mut parts = String::new();
    for (i, page) in pages.iter().enumerate() {
        cancel.check()?;
        if !page.is_empty() {
            let escaped = page
                .replace('&', "&amp;")
                .replace('<', "&lt;")
                .replace('>', "&gt;");
            parts.push_str("<p>");
            parts.push_str(&escaped.replace('\n', "<br>"));
            parts.push_str("</p>");
        }
        progress(
            (10 + 80 * (i + 1) / total) as u8,
            &format!("Processing page {}...", i + 1),
        );
    }

    // v2-style boilerplate page (Arial, max-width 800px, line-height 1.6).
    let html = format!(
        "<!DOCTYPE html>\n\
         <html><head><meta charset=\"UTF-8\"><title>Converted from PDF</title>\n\
         <style>body{{font-family:Arial,sans-serif;max-width:800px;margin:40px auto;line-height:1.6;}}</style>\n\
         </head><body>\n\
         {parts}\n\
         </body></html>"
    );

    let output = unique_output_path(&req.output_dir, stem, "html");
    fs::write(&output, html)
        .map_err(|e| ConvertError::with_detail("Failed to write HTML file", e.to_string()))?;
    progress(100, "Done");
    Ok(vec![output])
}

/// pdf → docx: extract text → temp `.md` → pandoc.
fn pdf_to_docx(
    req: &ConversionRequest,
    sidecars: &Sidecars,
    stem: &str,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    let pandoc = require_pandoc(sidecars)?;

    progress(10, "Extracting text from PDF...");
    let full_text = extracted_full_text(req, sidecars)?;
    cancel.check()?;

    let temp = tempfile::tempdir().map_err(|e| {
        ConvertError::with_detail("Failed to create temporary directory", e.to_string())
    })?;
    let md_path = temp.path().join("extracted.md");
    fs::write(&md_path, markdown_from_extracted(stem, &full_text)).map_err(|e| {
        ConvertError::with_detail("Failed to write temporary Markdown file", e.to_string())
    })?;

    progress(40, "Converting to Word with pandoc...");
    let output = unique_output_path(&req.output_dir, stem, "docx");
    let args = [
        md_path.as_os_str().to_owned(),
        OsString::from("-o"),
        output.as_os_str().to_owned(),
    ];
    run_pandoc(pandoc, &args, cancel, PANDOC_TIMEOUT, &output)?;
    progress(100, "Done");
    Ok(vec![output])
}

/// The general pandoc matrix: {md,html,docx,rtf,epub,txt} × targets,
/// including X → pdf via `--pdf-engine=<typst>`.
fn pandoc_convert(
    input: &Path,
    output_dir: &Path,
    stem: &str,
    target: &str,
    sidecars: &Sidecars,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    let pandoc = require_pandoc(sidecars)?;

    let output = unique_output_path(output_dir, stem, target);
    let mut args: Vec<OsString> = vec![
        input.as_os_str().to_owned(),
        OsString::from("-o"),
        output.as_os_str().to_owned(),
    ];
    let mut timeout = PANDOC_TIMEOUT;
    // Kept alive until pandoc finishes: the staged `typst`-named binary lives here.
    let mut _engine_dir: Option<tempfile::TempDir> = None;
    match target {
        "pdf" => {
            let typst = sidecars
                .typst
                .as_deref()
                .ok_or_else(|| ConvertError::new("Typst is required for PDF output"))?;
            // Pandoc validates the --pdf-engine argument by basename against its
            // known-engine list, so the bundled `typst-<triple>` sidecar is
            // rejected. Stage a copy named exactly `typst` and point pandoc at it.
            let (engine_path, dir) = stage_pdf_engine(typst)?;
            _engine_dir = dir;
            let mut engine = OsString::from("--pdf-engine=");
            engine.push(engine_path.as_os_str());
            args.push(engine);
            timeout = PDF_ENGINE_TIMEOUT;
        }
        "txt" => {
            args.push(OsString::from("-t"));
            args.push(OsString::from("plain"));
        }
        "html" => args.push(OsString::from("--standalone")),
        _ => {}
    }

    progress(15, "Converting with pandoc...");
    run_pandoc(pandoc, &args, cancel, timeout, &output)?;
    progress(100, "Done");
    Ok(vec![output])
}

/// Pandoc accepts `--pdf-engine` only when the argument's basename is a known
/// engine (`typst`). The bundled sidecar is named `typst-<triple>[.exe]`, so we
/// present pandoc a correctly-named binary. If the resolved typst already has
/// the right basename (the production case, where Tauri strips the suffix), it
/// is used directly; otherwise a `typst`-named copy is staged in a temp dir that
/// lives for the duration of the pandoc call.
fn stage_pdf_engine(typst: &Path) -> Result<(PathBuf, Option<tempfile::TempDir>), ConvertError> {
    let wanted = if cfg!(windows) { "typst.exe" } else { "typst" };
    if typst.file_name().and_then(|n| n.to_str()) == Some(wanted) {
        return Ok((typst.to_path_buf(), None));
    }
    let dir = tempfile::tempdir()
        .map_err(|e| ConvertError::new(format!("Could not stage the PDF engine: {e}")))?;
    let staged = dir.path().join(wanted);
    fs::copy(typst, &staged)
        .map_err(|e| ConvertError::new(format!("Could not stage the PDF engine: {e}")))?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = fs::set_permissions(&staged, fs::Permissions::from_mode(0o755));
    }
    Ok((staged, Some(dir)))
}

fn require_pandoc(sidecars: &Sidecars) -> Result<&Path, ConvertError> {
    sidecars
        .pandoc
        .as_deref()
        .ok_or_else(|| ConvertError::new("Pandoc is required for this conversion"))
}

/// Run pandoc via the shared sidecar runner; on any failure the (possibly
/// partial) output file is removed.
fn run_pandoc(
    bin: &Path,
    args: &[OsString],
    cancel: &CancelToken,
    timeout: Duration,
    output: &Path,
) -> Result<(), ConvertError> {
    match sidecar::run(bin, args, cancel, timeout, |_line| {}) {
        Ok(out) if out.status.success() => {
            if output.exists() {
                Ok(())
            } else {
                Err(ConvertError::new("Pandoc did not produce an output file"))
            }
        }
        Ok(out) => {
            let _ = fs::remove_file(output);
            let stderr = String::from_utf8_lossy(&out.stderr).trim().to_string();
            Err(ConvertError::with_detail(
                "Pandoc conversion failed",
                stderr,
            ))
        }
        Err(e) => {
            let _ = fs::remove_file(output);
            Err(e)
        }
    }
}
