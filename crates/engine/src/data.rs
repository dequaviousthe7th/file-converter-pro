//! Table conversions: csv/xlsx/tsv/json pairs + → html (csv, calamine,
//! rust_xlsxwriter, serde_json). Receives json → csv/xlsx/tsv via v2's
//! special JSON routing in `convert::convert`.
//!
//! Behavior (plan Task 4, v2 parity with documented deviations):
//! - csv/tsv read with headers, whole file decoded UTF-8 lossy.
//! - xlsx read via calamine (first sheet), every cell rendered to a string
//!   preserving display (integral floats without ".0", TRUE/FALSE booleans,
//!   date serials as ISO-ish strings).
//! - xlsx written via rust_xlsxwriter with a bold header row.
//! - json: array-of-objects ↔ table; column order = first-appearance union.
//!   Nested objects/arrays inside cells are serialized as compact JSON
//!   strings (deviation from v2's pandas `json_normalize`). A dict root uses
//!   the first value that is a non-empty array of objects, else errors.
//! - → json output: records orient, 2-space indent, non-ASCII preserved.
//!   All cells are emitted as JSON strings (deviation from pandas dtype
//!   inference).
//! - → html output: v2-style full styled page (#4a90d9 header, zebra rows,
//!   border-collapse).
//! - A table with zero data rows errors with "No data rows found".

use std::fs;
use std::path::{Path, PathBuf};

use calamine::{open_workbook, Data, Reader, Xlsx};
use serde_json::Value;

use crate::convert::{unique_output_path, ConversionRequest};
use crate::error::ConvertError;
use crate::job::{CancelToken, ProgressFn};
use crate::options::Sidecars;
use crate::registry;

/// In-memory table: header names + string cells (rows padded to header width).
struct Table {
    columns: Vec<String>,
    rows: Vec<Vec<String>>,
}

pub fn convert(
    req: &ConversionRequest,
    _sidecars: &Sidecars,
    cancel: &CancelToken,
    progress: ProgressFn,
) -> Result<Vec<PathBuf>, ConvertError> {
    let raw_ext = req
        .input
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or_default();
    let source = registry::normalize_ext(raw_ext);
    let target = registry::normalize_ext(&req.target);

    progress(10, "Loading data...");
    let table = match source {
        "csv" => read_delimited(&req.input, b',')?,
        "tsv" => read_delimited(&req.input, b'\t')?,
        "xlsx" => read_xlsx(&req.input)?,
        "json" => read_json(&req.input)?,
        other => {
            return Err(ConvertError::new(format!("Cannot read .{other} files")));
        }
    };
    if table.rows.is_empty() {
        return Err(ConvertError::new("No data rows found"));
    }

    cancel.check()?;
    progress(50, &format!("Converting to {}...", target.to_uppercase()));

    let stem = req
        .input
        .file_stem()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_else(|| "output".to_string());
    let out = unique_output_path(&req.output_dir, &stem, target);

    match target {
        "csv" => write_delimited(&table, &out, b',')?,
        "tsv" => write_delimited(&table, &out, b'\t')?,
        "xlsx" => write_xlsx(&table, &out)?,
        "json" => write_json(&table, &out)?,
        "html" => write_html(&table, &out)?,
        other => {
            return Err(ConvertError::new(format!(
                "Unsupported output format: {other}"
            )));
        }
    }

    progress(100, "Done");
    Ok(vec![out])
}

// ---------------------------------------------------------------- reading

fn read_lossy(path: &Path) -> Result<String, ConvertError> {
    let bytes = fs::read(path).map_err(|e| {
        ConvertError::with_detail(format!("Failed to read {}", path.display()), e.to_string())
    })?;
    Ok(String::from_utf8_lossy(&bytes).into_owned())
}

fn read_delimited(path: &Path, delimiter: u8) -> Result<Table, ConvertError> {
    let text = read_lossy(path)?;
    let mut reader = csv::ReaderBuilder::new()
        .delimiter(delimiter)
        .flexible(true)
        .from_reader(text.as_bytes());

    let columns: Vec<String> = reader
        .headers()
        .map_err(|e| ConvertError::with_detail("Failed to parse input file", e.to_string()))?
        .iter()
        .map(str::to_string)
        .collect();

    let mut rows = Vec::new();
    for (i, record) in reader.records().enumerate() {
        let record = record
            .map_err(|e| ConvertError::with_detail("Failed to parse input file", e.to_string()))?;
        if record.len() > columns.len() {
            return Err(ConvertError::new(format!(
                "Row {} has {} fields but the header has {}",
                i + 1,
                record.len(),
                columns.len()
            )));
        }
        let mut row: Vec<String> = record.iter().map(str::to_string).collect();
        row.resize(columns.len(), String::new());
        rows.push(row);
    }
    Ok(Table { columns, rows })
}

fn read_xlsx(path: &Path) -> Result<Table, ConvertError> {
    let mut workbook: Xlsx<_> = open_workbook(path).map_err(|e: calamine::XlsxError| {
        ConvertError::with_detail("Failed to open XLSX file", e.to_string())
    })?;
    let range = workbook
        .worksheet_range_at(0)
        .ok_or_else(|| ConvertError::new("XLSX file contains no worksheets"))?
        .map_err(|e| ConvertError::with_detail("Failed to read XLSX worksheet", e.to_string()))?;

    let mut row_iter = range.rows();
    let columns: Vec<String> = match row_iter.next() {
        Some(header) => header.iter().map(cell_to_string).collect(),
        None => Vec::new(),
    };
    let rows: Vec<Vec<String>> = row_iter
        .map(|r| {
            let mut row: Vec<String> = r.iter().map(cell_to_string).collect();
            row.resize(columns.len(), String::new());
            row
        })
        .collect();
    Ok(Table { columns, rows })
}

/// Render a calamine cell to its display string (v2 parity: what the user
/// sees in Excel, not the raw storage).
fn cell_to_string(cell: &Data) -> String {
    match cell {
        Data::Empty => String::new(),
        Data::String(s) => s.clone(),
        Data::Float(f) => float_display(*f),
        Data::Int(i) => i.to_string(),
        Data::Bool(b) => if *b { "TRUE" } else { "FALSE" }.to_string(),
        Data::DateTime(dt) => excel_serial_to_string(dt.as_f64()),
        Data::DateTimeIso(s) | Data::DurationIso(s) => s.clone(),
        Data::Error(e) => e.to_string(),
    }
}

/// Integral floats print without a fractional part (Excel displays 2, not 2.0).
fn float_display(f: f64) -> String {
    if f.is_finite() && f.fract() == 0.0 && f.abs() < 1e15 {
        format!("{}", f as i64)
    } else {
        f.to_string()
    }
}

/// Excel 1900-system date serial → "YYYY-MM-DD[ HH:MM:SS]" (time-only
/// serials < 1.0 → "HH:MM:SS"). No chrono: civil-from-days arithmetic.
fn excel_serial_to_string(serial: f64) -> String {
    if !serial.is_finite() || serial < 0.0 {
        return float_display(serial);
    }
    let mut days = serial.floor() as i64;
    let mut secs = ((serial - days as f64) * 86_400.0).round() as i64;
    if secs >= 86_400 {
        secs -= 86_400;
        days += 1;
    }
    let (h, m, s) = (secs / 3600, (secs % 3600) / 60, secs % 60);
    if days == 0 {
        return format!("{h:02}:{m:02}:{s:02}");
    }
    // Serial 25569 = 1970-01-01; serials < 61 predate Excel's phantom
    // 1900-02-29 and are offset by one.
    let unix_days = if days >= 61 {
        days - 25_569
    } else {
        days - 25_568
    };
    let (year, month, day) = civil_from_days(unix_days);
    if secs == 0 {
        format!("{year:04}-{month:02}-{day:02}")
    } else {
        format!("{year:04}-{month:02}-{day:02} {h:02}:{m:02}:{s:02}")
    }
}

/// Days since 1970-01-01 → (year, month, day). Howard Hinnant's algorithm.
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097; // [0, 146096]
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}

fn read_json(path: &Path) -> Result<Table, ConvertError> {
    let text = read_lossy(path)?;
    let root: Value = serde_json::from_str(&text)
        .map_err(|e| ConvertError::with_detail("Invalid JSON input", e.to_string()))?;

    let records: &[Value] = match &root {
        Value::Array(items) => items,
        Value::Object(map) => map
            .values()
            .find_map(|v| {
                v.as_array()
                    .filter(|a| !a.is_empty() && a[0].is_object())
                    .map(Vec::as_slice)
            })
            .ok_or_else(|| {
                ConvertError::new("JSON object contains no array of objects to convert")
            })?,
        _ => {
            return Err(ConvertError::new(
                "JSON structure not supported for tabular conversion",
            ));
        }
    };

    // Column order: first-appearance union across all row objects.
    let mut columns: Vec<String> = Vec::new();
    for item in records {
        let obj = item.as_object().ok_or_else(|| {
            ConvertError::new("JSON array items must be objects for tabular conversion")
        })?;
        for key in obj.keys() {
            if !columns.iter().any(|c| c == key) {
                columns.push(key.clone());
            }
        }
    }

    let rows: Vec<Vec<String>> = records
        .iter()
        .map(|item| {
            let obj = item.as_object().expect("validated above");
            columns
                .iter()
                .map(|c| obj.get(c).map(json_value_to_cell).unwrap_or_default())
                .collect()
        })
        .collect();
    Ok(Table { columns, rows })
}

/// Scalars render bare; null → empty; nested objects/arrays → compact JSON.
fn json_value_to_cell(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::String(s) => s.clone(),
        Value::Bool(b) => b.to_string(),
        Value::Number(n) => n.to_string(),
        nested => nested.to_string(),
    }
}

// ---------------------------------------------------------------- writing

fn write_delimited(table: &Table, path: &Path, delimiter: u8) -> Result<(), ConvertError> {
    let write_err =
        |e: csv::Error| ConvertError::with_detail("Failed to write output file", e.to_string());
    let mut writer = csv::WriterBuilder::new()
        .delimiter(delimiter)
        .from_path(path)
        .map_err(write_err)?;
    writer.write_record(&table.columns).map_err(write_err)?;
    for row in &table.rows {
        writer.write_record(row).map_err(write_err)?;
    }
    writer
        .flush()
        .map_err(|e| ConvertError::with_detail("Failed to write output file", e.to_string()))
}

fn write_xlsx(table: &Table, path: &Path) -> Result<(), ConvertError> {
    const MAX_COLS: usize = 16_384;
    const MAX_ROWS: usize = 1_048_575; // data rows; +1 header = Excel's limit
    if table.columns.len() > MAX_COLS {
        return Err(ConvertError::new(format!(
            "Too many columns for XLSX ({} > {MAX_COLS})",
            table.columns.len()
        )));
    }
    if table.rows.len() > MAX_ROWS {
        return Err(ConvertError::new(format!(
            "Too many rows for XLSX ({} > {MAX_ROWS})",
            table.rows.len()
        )));
    }

    let write_err = |e: rust_xlsxwriter::XlsxError| {
        ConvertError::with_detail("Failed to write XLSX file", e.to_string())
    };
    let mut workbook = rust_xlsxwriter::Workbook::new();
    let worksheet = workbook.add_worksheet();
    let bold = rust_xlsxwriter::Format::new().set_bold();
    for (col, name) in table.columns.iter().enumerate() {
        worksheet
            .write_string_with_format(0, col as u16, name, &bold)
            .map_err(write_err)?;
    }
    for (r, row) in table.rows.iter().enumerate() {
        for (c, cell) in row.iter().enumerate() {
            worksheet
                .write_string((r + 1) as u32, c as u16, cell)
                .map_err(write_err)?;
        }
    }
    workbook.save(path).map_err(write_err)
}

fn write_json(table: &Table, path: &Path) -> Result<(), ConvertError> {
    let records: Vec<Value> = table
        .rows
        .iter()
        .map(|row| {
            let mut obj = serde_json::Map::new();
            for (col, cell) in table.columns.iter().zip(row) {
                obj.insert(col.clone(), Value::String(cell.clone()));
            }
            Value::Object(obj)
        })
        .collect();
    // records orient, 2-space indent; serde_json leaves non-ASCII unescaped.
    let text = serde_json::to_string_pretty(&Value::Array(records))
        .map_err(|e| ConvertError::with_detail("Failed to serialize JSON", e.to_string()))?;
    fs::write(path, text)
        .map_err(|e| ConvertError::with_detail("Failed to write output file", e.to_string()))
}

fn write_html(table: &Table, path: &Path) -> Result<(), ConvertError> {
    let mut body = String::from("<table class=\"data-table\">\n<thead>\n<tr>");
    for col in &table.columns {
        body.push_str("<th>");
        body.push_str(&escape_html(col));
        body.push_str("</th>");
    }
    body.push_str("</tr>\n</thead>\n<tbody>\n");
    for row in &table.rows {
        body.push_str("<tr>");
        for cell in row {
            body.push_str("<td>");
            body.push_str(&escape_html(cell));
            body.push_str("</td>");
        }
        body.push_str("</tr>\n");
    }
    body.push_str("</tbody>\n</table>");

    // v2-style full styled page (data_converter.py parity).
    let html = format!(
        "<!DOCTYPE html>\n\
         <html><head><meta charset=\"UTF-8\"><title>Data Table</title>\n\
         <style>\n\
         body{{font-family:Arial,sans-serif;margin:40px;}}\n\
         table{{border-collapse:collapse;width:100%;}}\n\
         th,td{{border:1px solid #ddd;padding:8px;text-align:left;}}\n\
         th{{background:#4a90d9;color:white;}}\n\
         tr:nth-child(even){{background:#f2f2f2;}}\n\
         </style></head><body>\n\
         {body}\n\
         </body></html>"
    );
    fs::write(path, html)
        .map_err(|e| ConvertError::with_detail("Failed to write output file", e.to_string()))
}

fn escape_html(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for ch in s.chars() {
        match ch {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            _ => out.push(ch),
        }
    }
    out
}
