//! Audio + video conversions via the ffmpeg sidecar (all audio pairs, all
//! video pairs, video → gif two-pass palette).
//!
//! v2-parity parameters (binding, from the plan's "Media parameters" table):
//! - audio codec map: mp3=libmp3lame, wav=pcm_s16le, flac=flac, ogg=libvorbis,
//!   aac=`-f adts` aac, m4a=`-f ipod` aac, wma=`-f asf` wmav2;
//!   `-b:a {audio_bitrate}` for mp3/ogg/aac/m4a/wma; `-map_metadata 0`
//! - video codec map: mp4/mov=x264+aac+faststart, avi=x264+mp3, mkv=x264+aac,
//!   webm=vp9 2M + opus
//! - video→gif: two-pass palettegen/paletteuse (fps=10, scale=480 lanczos),
//!   palette in a temp dir removed afterwards
//! - progress: `-progress pipe:1 -nostats -y -hide_banner`, out_time ÷ input
//!   duration (probed from `ffmpeg -i` stderr), mapped to 5–95%

use std::ffi::OsString;
use std::path::{Path, PathBuf};
use std::time::Duration;

use crate::convert::{unique_output_path, ConversionRequest};
use crate::error::ConvertError;
use crate::job::{CancelToken, ProgressFn};
use crate::options::Sidecars;
use crate::registry;
use crate::sidecar;

/// Generous ceiling per ffmpeg pass — long videos are legitimate; the real
/// stop mechanisms are cancel and app exit.
const CONVERT_TIMEOUT: Duration = Duration::from_secs(60 * 60);
const PROBE_TIMEOUT: Duration = Duration::from_secs(60);

const AUDIO_TARGETS: &[&str] = &["mp3", "wav", "flac", "ogg", "aac", "m4a", "wma"];
/// Targets that take `-b:a {audio_bitrate}` (not lossless wav/flac).
const BITRATE_TARGETS: &[&str] = &["mp3", "ogg", "aac", "m4a", "wma"];

/// A single ffmpeg pass: the progress band it maps onto and its UI message.
struct Stage<'a> {
    lo: u8,
    hi: u8,
    message: &'a str,
}

pub fn convert(
    req: &ConversionRequest,
    sidecars: &Sidecars,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    let Some(ffmpeg) = sidecars.ffmpeg.as_deref() else {
        return Err(ConvertError::with_detail(
            "Audio/video conversion requires the bundled ffmpeg",
            "The ffmpeg sidecar binary was not found. Reinstalling File Converter Pro should restore it.",
        ));
    };
    cancel.check()?;

    let target_lower = req.target.to_ascii_lowercase();
    let target = registry::normalize_ext(&target_lower);
    let stem = req
        .input
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("output");
    let out = unique_output_path(&req.output_dir, stem, target);

    progress(2, "Analyzing input");
    let duration = probe_duration(ffmpeg, &req.input, cancel)?;
    cancel.check()?;

    if target == "gif" {
        video_to_gif(ffmpeg, req, &out, duration, cancel, progress)?;
    } else if AUDIO_TARGETS.contains(&target) {
        let args = audio_args(&req.input, &out, target, &req.options.audio_bitrate);
        let stage = Stage {
            lo: 5,
            hi: 95,
            message: "Converting audio",
        };
        run_ffmpeg(ffmpeg, &args, &out, duration, &stage, cancel, progress)?;
    } else {
        let args = video_args(&req.input, &out, target);
        let stage = Stage {
            lo: 5,
            hi: 95,
            message: "Converting video",
        };
        run_ffmpeg(ffmpeg, &args, &out, duration, &stage, cancel, progress)?;
    }

    if !out.exists() {
        return Err(ConvertError::new("ffmpeg did not produce an output file"));
    }
    progress(100, "Conversion complete");
    Ok(vec![out])
}

/// Two-pass video → gif (palettegen then paletteuse). The palette lives in a
/// temp dir inside the output dir and is removed when `palette_dir` drops —
/// including on every early-return/error path.
fn video_to_gif(
    ffmpeg: &Path,
    req: &ConversionRequest,
    out: &Path,
    duration: Option<f64>,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<(), ConvertError> {
    let palette_dir = tempfile::Builder::new()
        .prefix(".fcp-palette-")
        .tempdir_in(&req.output_dir)
        .map_err(|err| {
            ConvertError::with_detail("Failed to create palette temp directory", err.to_string())
        })?;
    let palette = palette_dir.path().join("palette.png");

    let mut pass1 = base_input_args(&req.input);
    pass1.push("-vf".into());
    pass1.push("fps=10,scale=480:-1:flags=lanczos,palettegen".into());
    let pass1 = finish_args(pass1, &palette);
    let stage1 = Stage {
        lo: 5,
        hi: 45,
        message: "Building color palette",
    };
    run_ffmpeg(
        ffmpeg, &pass1, &palette, duration, &stage1, cancel, progress,
    )?;
    cancel.check()?;

    let mut pass2 = base_input_args(&req.input);
    pass2.push("-i".into());
    pass2.push(palette.as_os_str().to_os_string());
    pass2.push("-lavfi".into());
    pass2.push("fps=10,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse".into());
    let pass2 = finish_args(pass2, out);
    let stage2 = Stage {
        lo: 45,
        hi: 95,
        message: "Rendering GIF",
    };
    run_ffmpeg(ffmpeg, &pass2, out, duration, &stage2, cancel, progress)?;

    drop(palette_dir); // explicit: palette temp removed here on success
    Ok(())
}

/// Runs one ffmpeg pass, mapping `out_time` progress into `[stage.lo, stage.hi]`.
/// On cancel/timeout/failure the partial `out` file is removed.
fn run_ffmpeg(
    ffmpeg: &Path,
    args: &[OsString],
    out: &Path,
    duration: Option<f64>,
    stage: &Stage<'_>,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<(), ConvertError> {
    progress(stage.lo, stage.message);
    let result = sidecar::run(ffmpeg, args, cancel, CONVERT_TIMEOUT, |line| {
        let Some(secs) = parse_out_time(line) else {
            return;
        };
        let Some(total) = duration else { return };
        if total <= 0.0 {
            return;
        }
        let frac = (secs / total).clamp(0.0, 1.0);
        let pct = f64::from(stage.lo) + frac * f64::from(stage.hi - stage.lo);
        progress(pct as u8, stage.message);
    });

    let output = match result {
        Ok(output) => output,
        Err(err) => {
            remove_partial(out);
            return Err(err);
        }
    };
    if !output.status.success() {
        remove_partial(out);
        return Err(ConvertError::with_detail(
            "ffmpeg conversion failed",
            stderr_tail(&output.stderr),
        ));
    }
    progress(stage.hi, stage.message);
    Ok(())
}

/// Input duration in seconds, parsed from `Duration: HH:MM:SS.cs` on the
/// stderr of `ffmpeg -i` (which exits non-zero by design — no output file).
/// `Ok(None)` when unparsable (e.g. `Duration: N/A`).
fn probe_duration(
    ffmpeg: &Path,
    input: &Path,
    cancel: &CancelToken,
) -> Result<Option<f64>, ConvertError> {
    let args: Vec<OsString> = vec![
        "-hide_banner".into(),
        "-i".into(),
        input.as_os_str().to_os_string(),
    ];
    let output = sidecar::run(ffmpeg, &args, cancel, PROBE_TIMEOUT, |_line| {})?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    Ok(parse_duration(&stderr))
}

fn parse_duration(stderr: &str) -> Option<f64> {
    let idx = stderr.find("Duration:")?;
    let rest = stderr[idx + "Duration:".len()..].trim_start();
    let token = rest.split([',', ' ', '\r', '\n']).next()?;
    parse_clock(token)
}

/// `HH:MM:SS.frac` → seconds.
fn parse_clock(clock: &str) -> Option<f64> {
    let mut parts = clock.split(':');
    let hours: f64 = parts.next()?.trim().parse().ok()?;
    let minutes: f64 = parts.next()?.trim().parse().ok()?;
    let seconds: f64 = parts.next()?.trim().parse().ok()?;
    if parts.next().is_some() {
        return None;
    }
    Some(hours * 3600.0 + minutes * 60.0 + seconds)
}

/// Seconds of media processed so far, from a `-progress pipe:1` line.
/// NB: ffmpeg's `out_time_ms` is actually microseconds (same as `out_time_us`).
fn parse_out_time(line: &str) -> Option<f64> {
    if let Some(value) = line
        .strip_prefix("out_time_us=")
        .or_else(|| line.strip_prefix("out_time_ms="))
    {
        return value.trim().parse::<f64>().ok().map(|us| us / 1_000_000.0);
    }
    if let Some(value) = line.strip_prefix("out_time=") {
        return parse_clock(value.trim());
    }
    None
}

fn audio_args(input: &Path, out: &Path, target: &str, bitrate: &str) -> Vec<OsString> {
    let mut args = base_input_args(input);
    args.push("-map_metadata".into());
    args.push("0".into());
    let codec: &[&str] = match target {
        "mp3" => &["-c:a", "libmp3lame"],
        "wav" => &["-c:a", "pcm_s16le"],
        "flac" => &["-c:a", "flac"],
        "ogg" => &["-c:a", "libvorbis"],
        "aac" => &["-c:a", "aac", "-f", "adts"],
        "m4a" => &["-c:a", "aac", "-f", "ipod"],
        "wma" => &["-c:a", "wmav2", "-f", "asf"],
        _ => &[],
    };
    args.extend(codec.iter().map(|s| OsString::from(*s)));
    if BITRATE_TARGETS.contains(&target) {
        args.push("-b:a".into());
        args.push(bitrate.into());
    }
    finish_args(args, out)
}

fn video_args(input: &Path, out: &Path, target: &str) -> Vec<OsString> {
    let mut args = base_input_args(input);
    let codec: &[&str] = match target {
        "mp4" | "mov" => &["-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart"],
        "avi" => &["-c:v", "libx264", "-c:a", "mp3"],
        "mkv" => &["-c:v", "libx264", "-c:a", "aac"],
        "webm" => &["-c:v", "libvpx-vp9", "-b:v", "2M", "-c:a", "libopus"],
        _ => &[],
    };
    args.extend(codec.iter().map(|s| OsString::from(*s)));
    finish_args(args, out)
}

fn base_input_args(input: &Path) -> Vec<OsString> {
    vec![
        "-hide_banner".into(),
        "-y".into(),
        "-i".into(),
        input.as_os_str().to_os_string(),
    ]
}

fn finish_args(mut args: Vec<OsString>, out: &Path) -> Vec<OsString> {
    args.push("-progress".into());
    args.push("pipe:1".into());
    args.push("-nostats".into());
    args.push(out.as_os_str().to_os_string());
    args
}

fn remove_partial(out: &Path) {
    if out.exists() {
        let _ = std::fs::remove_file(out);
    }
}

/// Last chunk of ffmpeg stderr for error detail (char-boundary safe).
fn stderr_tail(stderr: &[u8]) -> String {
    const MAX: usize = 2000;
    let text = String::from_utf8_lossy(stderr);
    let trimmed = text.trim();
    if trimmed.len() <= MAX {
        return trimmed.to_string();
    }
    let mut start = trimmed.len() - MAX;
    while !trimmed.is_char_boundary(start) {
        start += 1;
    }
    trimmed[start..].to_string()
}
