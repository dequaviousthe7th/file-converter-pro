//! Job registry + job execution: each conversion runs on a blocking task,
//! streams throttled `JobEvent`s over a `tauri::ipc::Channel`, and records
//! EVERY terminal state to history.

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use fcp_engine::convert::{convert, ConversionRequest};
use fcp_engine::job::CancelToken;
use fcp_engine::options::{ConvertOptions, Sidecars};
use serde::Serialize;
use tauri::ipc::Channel;
use tauri::{AppHandle, Manager, Runtime};

use crate::{history, settings, sidecars};

/// Channel payload (camelCase, tagged with `state`):
/// `{state:"running",pct,message} | {state:"done",outputs,duration} |
///  {state:"failed",message,detail} | {state:"cancelled"}`.
#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase", tag = "state")]
pub enum JobEvent {
    Running {
        pct: u8,
        message: String,
    },
    Done {
        outputs: Vec<String>,
        duration: f64,
    },
    Failed {
        message: String,
        detail: Option<String>,
    },
    Cancelled,
}

#[derive(Default)]
pub struct JobRegistry {
    next_id: AtomicU64,
    jobs: Mutex<HashMap<u64, CancelToken>>,
}

impl JobRegistry {
    fn register(&self) -> (u64, CancelToken) {
        let id = self.next_id.fetch_add(1, Ordering::SeqCst) + 1;
        let token = CancelToken::default();
        self.jobs.lock().unwrap().insert(id, token.clone());
        (id, token)
    }

    fn remove(&self, id: u64) {
        self.jobs.lock().unwrap().remove(&id);
    }

    pub fn cancel(&self, id: u64) {
        if let Some(token) = self.jobs.lock().unwrap().get(&id) {
            token.cancel();
        }
    }

    pub fn cancel_all(&self) {
        for token in self.jobs.lock().unwrap().values() {
            token.cancel();
        }
    }
}

/// Progress throttle: forward an update only when the percentage moved by
/// >= 1 point or >= 100ms elapsed since the last forwarded update.
struct ProgressThrottle {
    last_pct: Option<u8>,
    last_sent: Instant,
}

impl ProgressThrottle {
    fn new(now: Instant) -> Self {
        Self {
            last_pct: None,
            last_sent: now,
        }
    }

    fn should_send(&mut self, pct: u8, now: Instant) -> bool {
        let send = match self.last_pct {
            None => true,
            Some(previous) => {
                pct.abs_diff(previous) >= 1
                    || now.duration_since(self.last_sent) >= Duration::from_millis(100)
            }
        };
        if send {
            self.last_pct = Some(pct);
            self.last_sent = now;
        }
        send
    }
}

/// Register a job, resolve settings/sidecars, and run the conversion on a
/// blocking task. Returns the job id immediately.
pub fn start<R: Runtime>(
    app: AppHandle<R>,
    input: String,
    target: String,
    on_event: Channel<JobEvent>,
) -> Result<u64, String> {
    let settings = settings::load(&app)?;
    let output_dir = PathBuf::from(&settings.output_dir);
    // Default output dir is created on demand, right before the job runs.
    std::fs::create_dir_all(&output_dir)
        .map_err(|e| format!("Cannot create output folder {}: {e}", output_dir.display()))?;

    let request = ConversionRequest {
        input: PathBuf::from(&input),
        target,
        output_dir,
        options: ConvertOptions {
            image_quality: settings.image_quality,
            audio_bitrate: settings.audio_bitrate.clone(),
            pdf_dpi: settings.pdf_dpi,
        },
    };
    let resolved_sidecars = sidecars::resolve(&app);

    let (id, cancel) = app.state::<JobRegistry>().register();
    tauri::async_runtime::spawn_blocking(move || {
        run_job(&app, id, request, resolved_sidecars, cancel, on_event);
    });
    Ok(id)
}

fn run_job<R: Runtime>(
    app: &AppHandle<R>,
    id: u64,
    request: ConversionRequest,
    resolved_sidecars: Sidecars,
    cancel: CancelToken,
    on_event: Channel<JobEvent>,
) {
    let started = Instant::now();

    let throttle = Mutex::new(ProgressThrottle::new(started));
    let progress_channel = on_event.clone();
    let progress = |pct: u8, message: &str| {
        let mut gate = throttle.lock().unwrap();
        if gate.should_send(pct, Instant::now()) {
            let _ = progress_channel.send(JobEvent::Running {
                pct,
                message: message.to_string(),
            });
        }
    };

    let result = convert(&request, &resolved_sidecars, &cancel, &progress);
    let duration = history::round2(started.elapsed().as_secs_f64());

    match result {
        Ok(outputs) => {
            let record = history::record_now(
                &request.input,
                outputs.first().map(|p| p.as_path()),
                "success",
                duration,
            );
            let _ = history::add(app, record);
            let _ = on_event.send(JobEvent::Done {
                outputs: outputs.iter().map(|p| p.display().to_string()).collect(),
                duration,
            });
        }
        // Terminal state is Cancelled regardless of the error message.
        Err(_) if cancel.is_cancelled() => {
            let record = history::record_now(&request.input, None, "cancelled", duration);
            let _ = history::add(app, record);
            let _ = on_event.send(JobEvent::Cancelled);
        }
        Err(error) => {
            let record = history::record_now(&request.input, None, "failed", duration);
            let _ = history::add(app, record);
            let _ = on_event.send(JobEvent::Failed {
                message: error.message,
                detail: error.detail,
            });
        }
    }

    app.state::<JobRegistry>().remove(id);
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn registry_ids_are_unique_and_cancel_works() {
        let registry = JobRegistry::default();
        let (id1, token1) = registry.register();
        let (id2, token2) = registry.register();
        assert_ne!(id1, id2);
        registry.cancel(id1);
        assert!(token1.is_cancelled());
        assert!(!token2.is_cancelled());
        registry.cancel_all();
        assert!(token2.is_cancelled());
        registry.remove(id1);
        registry.remove(id2);
        assert!(registry.jobs.lock().unwrap().is_empty());
    }

    #[test]
    fn throttle_gates_by_delta_and_time() {
        let start = Instant::now();
        let mut throttle = ProgressThrottle::new(start);
        // First update always passes.
        assert!(throttle.should_send(0, start));
        // Same pct, no time elapsed -> suppressed.
        assert!(!throttle.should_send(0, start));
        // Delta >= 1 -> passes.
        assert!(throttle.should_send(1, start));
        // Same pct but 100ms elapsed -> passes.
        assert!(throttle.should_send(1, start + Duration::from_millis(100)));
        // Same pct, 99ms after last send -> suppressed.
        assert!(!throttle.should_send(1, start + Duration::from_millis(199)));
    }

    #[test]
    fn job_events_serialize_to_contract_shape() {
        let running = serde_json::to_value(JobEvent::Running {
            pct: 42,
            message: "Converting".to_string(),
        })
        .unwrap();
        assert_eq!(
            running,
            json!({"state": "running", "pct": 42, "message": "Converting"})
        );

        let done = serde_json::to_value(JobEvent::Done {
            outputs: vec!["/out/a_converted.jpg".to_string()],
            duration: 1.23,
        })
        .unwrap();
        assert_eq!(
            done,
            json!({"state": "done", "outputs": ["/out/a_converted.jpg"], "duration": 1.23})
        );

        let failed = serde_json::to_value(JobEvent::Failed {
            message: "boom".to_string(),
            detail: None,
        })
        .unwrap();
        assert_eq!(
            failed,
            json!({"state": "failed", "message": "boom", "detail": null})
        );

        let cancelled = serde_json::to_value(JobEvent::Cancelled).unwrap();
        assert_eq!(cancelled, json!({"state": "cancelled"}));
    }
}
