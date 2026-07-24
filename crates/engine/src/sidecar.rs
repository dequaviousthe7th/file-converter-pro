//! Sidecar process runner: spawn with timeout, kill-on-cancel,
//! CREATE_NO_WINDOW on Windows, stdout+stderr capture.
//!
//! The child is polled every ~100ms; on cancel or timeout it is killed AND
//! waited (reaped), so no orphaned ffmpeg/pandoc processes survive (fixes the
//! v2 orphan bug). Both stdout and stderr are drained on reader threads so
//! the child can never block on a full pipe; every line is also streamed to
//! `on_line` for progress parsing.

use std::ffi::OsString;
use std::io::{BufRead, BufReader, Read};
use std::path::Path;
use std::process::{Command, Output, Stdio};
use std::sync::mpsc::{Receiver, Sender};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use crate::error::ConvertError;
use crate::job::CancelToken;

const POLL_INTERVAL: Duration = Duration::from_millis(100);

/// Run a sidecar binary to completion, streaming stderr/stdout lines to
/// `on_line`. Polls the child every ~100ms; kills + waits on cancel or
/// timeout (no orphaned processes).
///
/// Returns `Ok(Output)` whenever the process ran to completion — including
/// non-zero exit codes; callers inspect `output.status` (the duration probe
/// deliberately runs `ffmpeg -i` which exits non-zero).
pub fn run(
    bin: &Path,
    args: &[OsString],
    cancel: &CancelToken,
    timeout: Duration,
    mut on_line: impl FnMut(&str),
) -> Result<Output, ConvertError> {
    let mut command = Command::new(bin);
    command
        .args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    let mut child = command.spawn().map_err(|err| {
        ConvertError::with_detail(
            format!("Failed to launch {}", display_name(bin)),
            err.to_string(),
        )
    })?;

    let (tx, rx) = std::sync::mpsc::channel::<String>();
    let stdout_pump = pump(child.stdout.take(), tx.clone());
    let stderr_pump = pump(child.stderr.take(), tx);

    let started = Instant::now();
    let status = loop {
        drain_lines(&rx, &mut on_line);

        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) => {}
            Err(err) => {
                let _ = child.kill();
                let _ = child.wait();
                let _ = stdout_pump.join();
                let _ = stderr_pump.join();
                return Err(ConvertError::with_detail(
                    format!("Failed to poll {}", display_name(bin)),
                    err.to_string(),
                ));
            }
        }

        if cancel.is_cancelled() {
            let _ = child.kill();
            let _ = child.wait();
            let _ = stdout_pump.join();
            let _ = stderr_pump.join();
            return Err(ConvertError::new("Conversion cancelled"));
        }

        if started.elapsed() >= timeout {
            let _ = child.kill();
            let _ = child.wait();
            let _ = stdout_pump.join();
            let _ = stderr_pump.join();
            return Err(ConvertError::with_detail(
                format!("{} timed out after {:?}", display_name(bin), timeout),
                "The process was killed.",
            ));
        }

        std::thread::sleep(POLL_INTERVAL);
    };

    // Child has exited: the pipes are closed, so the reader threads finish.
    let stdout = stdout_pump.join().unwrap_or_default();
    let stderr = stderr_pump.join().unwrap_or_default();
    drain_lines(&rx, &mut on_line);

    Ok(Output {
        status,
        stdout,
        stderr,
    })
}

/// Reads a child pipe to EOF on a thread, collecting raw bytes for
/// `Output` and forwarding each (CR- or LF-terminated) line to the channel.
fn pump<R: Read + Send + 'static>(stream: Option<R>, tx: Sender<String>) -> JoinHandle<Vec<u8>> {
    std::thread::spawn(move || {
        let mut collected = Vec::new();
        let Some(stream) = stream else {
            return collected;
        };
        let mut reader = BufReader::new(stream);
        let mut buf = Vec::new();
        loop {
            buf.clear();
            match reader.read_until(b'\n', &mut buf) {
                Ok(0) | Err(_) => break,
                Ok(_) => {
                    collected.extend_from_slice(&buf);
                    for line in String::from_utf8_lossy(&buf).split(['\r', '\n']) {
                        let line = line.trim();
                        if !line.is_empty() {
                            // Receiver gone (early return) — keep collecting bytes.
                            let _ = tx.send(line.to_string());
                        }
                    }
                }
            }
        }
        collected
    })
}

fn drain_lines(rx: &Receiver<String>, on_line: &mut impl FnMut(&str)) {
    for line in rx.try_iter() {
        on_line(&line);
    }
}

fn display_name(bin: &Path) -> String {
    bin.file_name().map_or_else(
        || bin.display().to_string(),
        |name| name.to_string_lossy().into_owned(),
    )
}
