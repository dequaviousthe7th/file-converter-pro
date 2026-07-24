//! Conversion history: JSON file in the app-data dir, newest first,
//! capped at 200 records. Record schema matches v2 (camelCase on the wire):
//! `{ source, output, sourceName, outputName, timestamp, datetime, status, duration }`.

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use serde_json::Value;
use tauri::{AppHandle, Manager, Runtime};

const HISTORY_FILE: &str = "history.json";
const CAP: usize = 200;

/// Serializes file reads/modify/writes across job threads.
static LOCK: Mutex<()> = Mutex::new(());

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct HistoryRecord {
    pub source: String,
    pub output: String,
    pub source_name: String,
    pub output_name: String,
    pub timestamp: f64,
    pub datetime: String,
    pub status: String,
    pub duration: f64,
}

/// Round to 2 decimal places (duration seconds, v2 parity).
pub(crate) fn round2(value: f64) -> f64 {
    (value * 100.0).round() / 100.0
}

/// Build a record for a job that just reached a terminal state.
pub fn record_now(
    source: &Path,
    output: Option<&Path>,
    status: &str,
    duration: f64,
) -> HistoryRecord {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let name_of = |p: &Path| {
        p.file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default()
    };
    HistoryRecord {
        source: source.display().to_string(),
        output: output.map(|p| p.display().to_string()).unwrap_or_default(),
        source_name: name_of(source),
        output_name: output.map(name_of).unwrap_or_default(),
        timestamp: now.as_secs_f64(),
        datetime: format_datetime(now.as_secs() as i64),
        status: status.to_string(),
        duration: round2(duration),
    }
}

/// `YYYY-MM-DD HH:MM` (UTC) from unix seconds.
/// (v2 recorded local time; std has no timezone database, so v3 records UTC —
/// the frontend formats `timestamp` locally for display.)
pub(crate) fn format_datetime(epoch_secs: i64) -> String {
    let days = epoch_secs.div_euclid(86_400);
    let secs_of_day = epoch_secs.rem_euclid(86_400);
    let (year, month, day) = civil_from_days(days);
    let hour = secs_of_day / 3_600;
    let minute = (secs_of_day % 3_600) / 60;
    format!("{year:04}-{month:02}-{day:02} {hour:02}:{minute:02}")
}

/// Howard Hinnant's `civil_from_days`: days since 1970-01-01 → (y, m, d).
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097; // [0, 146096]
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365; // [0, 399]
    let year = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100); // [0, 365]
    let mp = (5 * doy + 2) / 153; // [0, 11]
    let day = (doy - (153 * mp + 2) / 5 + 1) as u32; // [1, 31]
    let month = (if mp < 10 { mp + 3 } else { mp - 9 }) as u32; // [1, 12]
    (year + i64::from(month <= 2), month, day)
}

fn file_path<R: Runtime>(app: &AppHandle<R>) -> Result<PathBuf, String> {
    let dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir.join(HISTORY_FILE))
}

fn read(path: &Path) -> Vec<HistoryRecord> {
    fs::read_to_string(path)
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_default()
}

fn write(path: &Path, records: &[HistoryRecord]) -> Result<(), String> {
    let text = serde_json::to_string_pretty(records).map_err(|e| e.to_string())?;
    fs::write(path, text).map_err(|e| e.to_string())
}

/// Most recent `limit` records (0 = all, still capped at 200 on disk).
pub fn load<R: Runtime>(app: &AppHandle<R>, limit: usize) -> Vec<HistoryRecord> {
    let _guard = LOCK.lock().unwrap();
    let Ok(path) = file_path(app) else {
        return Vec::new();
    };
    let mut records = read(&path);
    if limit > 0 && records.len() > limit {
        records.truncate(limit);
    }
    records
}

/// Prepend a record (newest first), cap at 200, persist. Best-effort.
pub fn add<R: Runtime>(app: &AppHandle<R>, record: HistoryRecord) -> Result<(), String> {
    let _guard = LOCK.lock().unwrap();
    let path = file_path(app)?;
    let mut records = read(&path);
    records.insert(0, record);
    records.truncate(CAP);
    write(&path, &records)
}

pub fn clear<R: Runtime>(app: &AppHandle<R>) -> Result<(), String> {
    let _guard = LOCK.lock().unwrap();
    let path = file_path(app)?;
    write(&path, &[])
}

/// One-time v2 import: copy `~/.file-converter-pro/history.json` records
/// (snake_case v2 schema) into the new store — only when no v3 history
/// file exists yet.
pub fn import_v2<R: Runtime>(app: &AppHandle<R>, v2_file: &Path) {
    let _guard = LOCK.lock().unwrap();
    let Ok(path) = file_path(app) else {
        return;
    };
    if path.exists() {
        return;
    }
    let Ok(text) = fs::read_to_string(v2_file) else {
        return;
    };
    let Ok(value) = serde_json::from_str::<Value>(&text) else {
        return;
    };
    let Some(array) = value.as_array() else {
        return;
    };
    let records: Vec<HistoryRecord> = array.iter().filter_map(record_from_v2).take(CAP).collect();
    if records.is_empty() {
        return;
    }
    let _ = write(&path, &records);
}

/// Map one v2 (snake_case) history record; non-objects are skipped.
pub(crate) fn record_from_v2(value: &Value) -> Option<HistoryRecord> {
    let obj = value.as_object()?;
    let text = |key: &str| {
        obj.get(key)
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_string()
    };
    let number = |key: &str| obj.get(key).and_then(Value::as_f64).unwrap_or_default();
    Some(HistoryRecord {
        source: text("source"),
        output: text("output"),
        source_name: text("source_name"),
        output_name: text("output_name"),
        timestamp: number("timestamp"),
        datetime: text("datetime"),
        status: text("status"),
        duration: round2(number("duration")),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn datetime_epoch_zero() {
        assert_eq!(format_datetime(0), "1970-01-01 00:00");
    }

    #[test]
    fn datetime_leap_year_boundary() {
        // date -u -d "2000-03-01 00:00" +%s == 951868800
        assert_eq!(format_datetime(951_868_800), "2000-03-01 00:00");
        // date -u -d "1999-12-31 23:59" +%s == 946684740
        assert_eq!(format_datetime(946_684_740), "1999-12-31 23:59");
    }

    #[test]
    fn datetime_current_era() {
        // date -u -d "2026-07-25 12:34" +%s == 1784982840
        assert_eq!(format_datetime(1_784_982_840), "2026-07-25 12:34");
    }

    #[test]
    fn round2_rounds_half_up() {
        assert_eq!(round2(1.005), 1.01);
        assert_eq!(round2(2.0), 2.0);
        assert_eq!(round2(0.123), 0.12);
    }

    #[test]
    fn record_serializes_camel_case() {
        let record = record_now(
            Path::new("/tmp/in.png"),
            Some(Path::new("/tmp/in_converted.jpg")),
            "success",
            1.234,
        );
        let value = serde_json::to_value(&record).unwrap();
        let obj = value.as_object().unwrap();
        for key in [
            "source",
            "output",
            "sourceName",
            "outputName",
            "timestamp",
            "datetime",
            "status",
            "duration",
        ] {
            assert!(obj.contains_key(key), "missing key {key}");
        }
        assert_eq!(obj["sourceName"], "in.png");
        assert_eq!(obj["outputName"], "in_converted.jpg");
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["duration"], 1.23);
    }

    #[test]
    fn v2_record_maps_snake_case_fields() {
        let v2 = json!({
            "source": "C:/a.png",
            "output": "C:/a_converted.jpg",
            "source_name": "a.png",
            "output_name": "a_converted.jpg",
            "timestamp": 1700000000.5,
            "datetime": "2023-11-14 22:13",
            "status": "success",
            "duration": 0.789
        });
        let record = record_from_v2(&v2).unwrap();
        assert_eq!(record.source_name, "a.png");
        assert_eq!(record.output_name, "a_converted.jpg");
        assert_eq!(record.timestamp, 1_700_000_000.5);
        assert_eq!(record.datetime, "2023-11-14 22:13");
        assert_eq!(record.duration, 0.79);
        assert!(record_from_v2(&json!("not an object")).is_none());
    }
}
