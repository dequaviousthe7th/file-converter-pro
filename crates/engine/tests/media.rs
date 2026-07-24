//! Integration tests for the ffmpeg-backed media module (Task 6) and the
//! sidecar process runner.
//!
//! ffmpeg-dependent tests run only when `FCP_FFMPEG` points at a binary or a
//! system `ffmpeg` is on PATH; otherwise they skip silently so CI without
//! ffmpeg stays green. Fixtures are generated with ffmpeg itself.

use std::ffi::OsString;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU8, Ordering};
use std::time::{Duration, Instant};

use fcp_engine::convert::{convert, ConversionRequest};
use fcp_engine::error::ConvertError;
use fcp_engine::job::CancelToken;
use fcp_engine::options::{ConvertOptions, Sidecars};
use fcp_engine::sidecar;

fn ffmpeg_path() -> Option<PathBuf> {
    if let Ok(path) = std::env::var("FCP_FFMPEG") {
        let path = PathBuf::from(path);
        if path.exists() {
            return Some(path);
        }
    }
    let candidate = PathBuf::from("ffmpeg");
    match Command::new(&candidate).arg("-version").output() {
        Ok(out) if out.status.success() => Some(candidate),
        _ => None,
    }
}

macro_rules! require_ffmpeg {
    () => {
        match ffmpeg_path() {
            Some(path) => path,
            None => {
                eprintln!("skipping: ffmpeg not available");
                return;
            }
        }
    };
}

fn sidecars_with(ffmpeg: &Path) -> Sidecars {
    Sidecars {
        ffmpeg: Some(ffmpeg.to_path_buf()),
        ..Sidecars::default()
    }
}

fn gen_fixture(ffmpeg: &Path, args: &[&str], out: &Path) {
    let status = Command::new(ffmpeg)
        .args(["-hide_banner", "-y"])
        .args(args)
        .arg(out)
        .status()
        .expect("failed to run ffmpeg for fixture generation");
    assert!(status.success(), "fixture generation failed: {args:?}");
    assert!(out.exists(), "fixture missing: {}", out.display());
}

/// 440 Hz mono sine tone, `secs` seconds, WAV.
fn gen_sine_wav(ffmpeg: &Path, dir: &Path, secs: u32) -> PathBuf {
    let out = dir.join("tone.wav");
    gen_fixture(
        ffmpeg,
        &[
            "-f",
            "lavfi",
            "-i",
            &format!("sine=frequency=440:duration={secs}"),
            "-ac",
            "1",
        ],
        &out,
    );
    out
}

/// `secs` seconds of the testsrc pattern, 320x240 @ 30fps, H.264 MP4.
fn gen_testsrc_mp4(ffmpeg: &Path, dir: &Path, secs: u32) -> PathBuf {
    let out = dir.join("clip.mp4");
    gen_fixture(
        ffmpeg,
        &[
            "-f",
            "lavfi",
            "-i",
            &format!("testsrc=duration={secs}:size=320x240:rate=30"),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
        ],
        &out,
    );
    out
}

fn request(input: &Path, target: &str, out_dir: &Path) -> ConversionRequest {
    ConversionRequest {
        input: input.to_path_buf(),
        target: target.to_string(),
        output_dir: out_dir.to_path_buf(),
        options: ConvertOptions::default(),
    }
}

/// Runs a conversion recording the highest progress percentage reported.
fn run_tracking_progress(
    req: &ConversionRequest,
    sidecars: &Sidecars,
) -> (Result<Vec<PathBuf>, ConvertError>, u8) {
    let max_pct = AtomicU8::new(0);
    let progress = |pct: u8, _msg: &str| {
        max_pct.fetch_max(pct, Ordering::SeqCst);
    };
    let result = convert(req, sidecars, &CancelToken::default(), &progress);
    (result, max_pct.load(Ordering::SeqCst))
}

#[test]
fn wav_to_mp3_produces_output_and_reaches_full_progress() {
    let ffmpeg = require_ffmpeg!();
    let in_dir = tempfile::tempdir().unwrap();
    let out_dir = tempfile::tempdir().unwrap();
    let wav = gen_sine_wav(&ffmpeg, in_dir.path(), 1);

    let req = request(&wav, "mp3", out_dir.path());
    let (result, max_pct) = run_tracking_progress(&req, &sidecars_with(&ffmpeg));

    let outputs = result.expect("wav -> mp3 conversion failed");
    assert_eq!(outputs.len(), 1);
    assert_eq!(outputs[0], out_dir.path().join("tone_converted.mp3"));
    let size = std::fs::metadata(&outputs[0]).unwrap().len();
    assert!(size > 1024, "mp3 too small: {size} bytes");
    assert!(max_pct >= 95, "progress never reached 95 (max {max_pct})");
}

#[test]
fn wav_to_flac_produces_valid_flac() {
    let ffmpeg = require_ffmpeg!();
    let in_dir = tempfile::tempdir().unwrap();
    let out_dir = tempfile::tempdir().unwrap();
    let wav = gen_sine_wav(&ffmpeg, in_dir.path(), 1);

    let req = request(&wav, "flac", out_dir.path());
    let (result, _) = run_tracking_progress(&req, &sidecars_with(&ffmpeg));

    let outputs = result.expect("wav -> flac conversion failed");
    assert_eq!(outputs.len(), 1);
    assert_eq!(outputs[0], out_dir.path().join("tone_converted.flac"));
    let bytes = std::fs::read(&outputs[0]).unwrap();
    assert!(bytes.len() > 1024, "flac too small: {} bytes", bytes.len());
    assert_eq!(&bytes[..4], b"fLaC", "missing fLaC magic");
}

#[test]
fn cancel_kills_ffmpeg_and_removes_partial_output() {
    let ffmpeg = require_ffmpeg!();
    let in_dir = tempfile::tempdir().unwrap();
    let out_dir = tempfile::tempdir().unwrap();
    // 30s VP9 encode: guaranteed to still be running when we cancel at ~200ms.
    let mp4 = gen_testsrc_mp4(&ffmpeg, in_dir.path(), 30);

    let req = request(&mp4, "webm", out_dir.path());
    let cancel = CancelToken::default();
    let canceller = {
        let cancel = cancel.clone();
        std::thread::spawn(move || {
            std::thread::sleep(Duration::from_millis(200));
            cancel.cancel();
        })
    };

    let started = Instant::now();
    let err = convert(&req, &sidecars_with(&ffmpeg), &cancel, &|_pct, _msg| {}).unwrap_err();
    canceller.join().unwrap();

    assert!(
        err.message.to_lowercase().contains("cancelled"),
        "unexpected error: {}",
        err.message
    );
    // Kill must be prompt — nowhere near the ~10s+ a full 30s VP9 encode takes.
    assert!(
        started.elapsed() < Duration::from_secs(10),
        "cancel did not kill the child promptly ({:?})",
        started.elapsed()
    );
    // Partial output cleaned up.
    let leftovers: Vec<_> = std::fs::read_dir(out_dir.path())
        .unwrap()
        .map(|e| e.unwrap().file_name())
        .collect();
    assert!(leftovers.is_empty(), "partial output left: {leftovers:?}");
    // Child dead: no ffmpeg process still references our unique output dir
    // (best effort — skipped if pgrep is unavailable).
    if let Ok(out) = Command::new("pgrep")
        .args(["-f", out_dir.path().to_str().unwrap()])
        .output()
    {
        assert!(
            !out.status.success(),
            "an ffmpeg process still references the output dir"
        );
    }
}

#[test]
fn timeout_kills_overlong_job() {
    let ffmpeg = require_ffmpeg!();
    // arealtime throttles to real time: this job would take ~30s.
    let args: Vec<OsString> = [
        "-hide_banner",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=30",
        "-af",
        "arealtime",
        "-f",
        "null",
        "-",
    ]
    .iter()
    .map(|s| OsString::from(*s))
    .collect();

    let started = Instant::now();
    let err = sidecar::run(
        &ffmpeg,
        &args,
        &CancelToken::default(),
        Duration::from_millis(400),
        |_line| {},
    )
    .unwrap_err();

    assert!(
        err.message.contains("timed out"),
        "unexpected error: {}",
        err.message
    );
    assert!(
        started.elapsed() < Duration::from_secs(10),
        "timeout did not kill the child promptly ({:?})",
        started.elapsed()
    );
}

#[test]
fn mp4_to_webm_converts_with_progress() {
    let ffmpeg = require_ffmpeg!();
    let in_dir = tempfile::tempdir().unwrap();
    let out_dir = tempfile::tempdir().unwrap();
    let mp4 = gen_testsrc_mp4(&ffmpeg, in_dir.path(), 2);

    let req = request(&mp4, "webm", out_dir.path());
    let (result, max_pct) = run_tracking_progress(&req, &sidecars_with(&ffmpeg));

    let outputs = result.expect("mp4 -> webm conversion failed");
    assert_eq!(outputs.len(), 1);
    assert_eq!(outputs[0], out_dir.path().join("clip_converted.webm"));
    let size = std::fs::metadata(&outputs[0]).unwrap().len();
    assert!(size > 1024, "webm too small: {size} bytes");
    assert!(max_pct >= 95, "progress never reached 95 (max {max_pct})");
}

#[test]
fn mp4_to_gif_two_pass_cleans_palette_temp() {
    let ffmpeg = require_ffmpeg!();
    let in_dir = tempfile::tempdir().unwrap();
    let out_dir = tempfile::tempdir().unwrap();
    let mp4 = gen_testsrc_mp4(&ffmpeg, in_dir.path(), 2);

    let req = request(&mp4, "gif", out_dir.path());
    let (result, max_pct) = run_tracking_progress(&req, &sidecars_with(&ffmpeg));

    let outputs = result.expect("mp4 -> gif conversion failed");
    assert_eq!(outputs.len(), 1);
    assert_eq!(outputs[0], out_dir.path().join("clip_converted.gif"));
    let bytes = std::fs::read(&outputs[0]).unwrap();
    assert!(bytes.len() > 1024, "gif too small: {} bytes", bytes.len());
    assert_eq!(&bytes[..4], b"GIF8", "missing GIF magic");
    assert!(max_pct >= 95, "progress never reached 95 (max {max_pct})");
    // The palette temp dir lives inside the output dir during conversion and
    // must be gone afterwards: only the gif remains.
    let entries: Vec<_> = std::fs::read_dir(out_dir.path())
        .unwrap()
        .map(|e| e.unwrap().file_name())
        .collect();
    assert_eq!(
        entries,
        vec![std::ffi::OsString::from("clip_converted.gif")],
        "palette temp not cleaned: {entries:?}"
    );
}

#[test]
fn sidecar_reports_missing_binary() {
    let err = sidecar::run(
        Path::new("/nonexistent/fcp-test-binary"),
        &[],
        &CancelToken::default(),
        Duration::from_secs(1),
        |_line| {},
    )
    .unwrap_err();
    assert!(
        err.message.contains("Failed to launch"),
        "unexpected error: {}",
        err.message
    );
}

#[test]
fn media_without_ffmpeg_sidecar_gives_helpful_error() {
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("song.wav");
    std::fs::write(&input, b"dummy").unwrap();

    let req = request(&input, "mp3", dir.path());
    let err = convert(
        &req,
        &Sidecars::default(),
        &CancelToken::default(),
        &|_pct, _msg| {},
    )
    .unwrap_err();

    assert!(
        err.message.contains("ffmpeg"),
        "unexpected error: {}",
        err.message
    );
    assert!(err.detail.is_some(), "expected a helpful detail");
}
