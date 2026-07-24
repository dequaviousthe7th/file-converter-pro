//! Config trio conversions: json/yaml/toml via a `serde_json::Value` hub
//! (`preserve_order` keeps key order end to end).
//!
//! - YAML: `serde-saphyr` with `strict_booleans` (YAML 1.2 — `no`/`on`/`yes`
//!   stay strings); output is block style with 2-space indent, insertion order.
//! - TOML input: parsed with `toml::de::DeTable` and re-ordered by source
//!   spans, because this build of the `toml` crate lacks `preserve_order`
//!   (BTreeMap-backed tables iterate alphabetically). Datetimes become their
//!   RFC 3339 string form; non-finite floats are explicit errors.
//! - TOML output: emitted by a small writer so nulls, u64 overflow and root
//!   type problems produce clear errors naming the key path, and key order is
//!   preserved (`key = value` lines first, then `[table]` / `[[array]]`
//!   sections in insertion order).
//! - JSON output: 2-space indent, non-ASCII written literally.
//!
//! Receives json → yaml/toml via v2's special JSON routing in
//! `convert::convert` (json → csv/xlsx/tsv goes to `data`).

use std::fmt::Write as _;
use std::fs;
use std::path::PathBuf;

use serde_json::Value;
use toml::de::{DeArray, DeTable, DeValue};

use crate::convert::{unique_output_path, ConversionRequest};
use crate::error::ConvertError;
use crate::job::{CancelToken, ProgressFn};
use crate::options::Sidecars;
use crate::registry;

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

    progress(5, "Reading input");
    let text = read_text(req)?;
    cancel.check()?;

    progress(30, &format!("Parsing {}", source.to_uppercase()));
    let value = match source {
        "json" => parse_json(&text)?,
        "yaml" => parse_yaml(&text)?,
        "toml" => parse_toml(&text)?,
        other => {
            return Err(ConvertError::new(format!(
                "Unsupported config source format: {other}"
            )))
        }
    };
    cancel.check()?;

    progress(70, &format!("Writing {}", target.to_uppercase()));
    let output_text = match target {
        "json" => to_json_string(&value)?,
        "yaml" => to_yaml_string(&value)?,
        "toml" => to_toml_string(&value)?,
        other => {
            return Err(ConvertError::new(format!(
                "Unsupported config target format: {other}"
            )))
        }
    };
    cancel.check()?;

    let stem = req
        .input
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("output");
    let output = unique_output_path(&req.output_dir, stem, target);
    fs::write(&output, output_text).map_err(|e| {
        ConvertError::with_detail(
            format!("Failed to write output file: {}", output.display()),
            e.to_string(),
        )
    })?;

    progress(100, "Done");
    Ok(vec![output])
}

// ------------------------------------------------------------------ reading

fn read_text(req: &ConversionRequest) -> Result<String, ConvertError> {
    let bytes = fs::read(&req.input).map_err(|e| {
        ConvertError::with_detail(
            format!("Failed to read input file: {}", req.input.display()),
            e.to_string(),
        )
    })?;
    let text = String::from_utf8(bytes).map_err(|_| {
        ConvertError::new(format!(
            "Input file is not valid UTF-8: {}",
            req.input.display()
        ))
    })?;
    // Tolerate a UTF-8 BOM (common on Windows); the parsers reject it.
    Ok(text.strip_prefix('\u{feff}').unwrap_or(&text).to_string())
}

// ------------------------------------------------------------------ parsing

fn parse_json(text: &str) -> Result<Value, ConvertError> {
    serde_json::from_str(text)
        .map_err(|e| ConvertError::with_detail("Failed to parse JSON input", e.to_string()))
}

fn parse_yaml(text: &str) -> Result<Value, ConvertError> {
    // strict_booleans: YAML 1.2 semantics — only `true`/`false` are booleans;
    // YAML 1.1 spellings (`no`/`on`/`yes`/`off`) stay strings.
    let options = serde_saphyr::options! { strict_booleans: true };
    serde_saphyr::from_str_with_options(text, options)
        .map_err(|e| ConvertError::with_detail("Failed to parse YAML input", e.to_string()))
}

fn parse_toml(text: &str) -> Result<Value, ConvertError> {
    let root = DeTable::parse(text)
        .map_err(|e| ConvertError::with_detail("Failed to parse TOML input", e.to_string()))?;
    let mut path = Vec::new();
    detable_to_value(root.get_ref(), &mut path)
}

/// Convert a parsed TOML table to a JSON object, restoring source order.
///
/// Without the `preserve_order` feature the `toml` crate stores tables in a
/// BTreeMap (alphabetical); sorting entries by their source span recovers the
/// order the keys appear in the document.
fn detable_to_value(table: &DeTable<'_>, path: &mut Vec<String>) -> Result<Value, ConvertError> {
    let mut entries: Vec<_> = table.iter().collect();
    entries.sort_by_key(|(key, _)| key.span().start);

    let mut map = serde_json::Map::with_capacity(entries.len());
    for (key, val) in entries {
        let name = key.get_ref().to_string();
        path.push(name.clone());
        let converted = devalue_to_value(val.get_ref(), path)?;
        path.pop();
        map.insert(name, converted);
    }
    Ok(Value::Object(map))
}

fn dearray_to_value(array: &DeArray<'_>, path: &mut Vec<String>) -> Result<Value, ConvertError> {
    let mut items = Vec::with_capacity(array.len());
    for (index, item) in array.iter().enumerate() {
        path.push(format!("[{index}]"));
        items.push(devalue_to_value(item.get_ref(), path)?);
        path.pop();
    }
    Ok(Value::Array(items))
}

fn devalue_to_value(value: &DeValue<'_>, path: &mut Vec<String>) -> Result<Value, ConvertError> {
    match value {
        DeValue::String(s) => Ok(Value::String(s.to_string())),
        DeValue::Boolean(b) => Ok(Value::Bool(*b)),
        DeValue::Integer(i) => {
            if let Ok(v) = i64::from_str_radix(i.as_str(), i.radix()) {
                Ok(Value::from(v))
            } else if let Ok(v) = u64::from_str_radix(i.as_str(), i.radix()) {
                Ok(Value::from(v))
            } else {
                Err(ConvertError::new(format!(
                    "TOML integer at '{}' is out of range: {i}",
                    path_string(path)
                )))
            }
        }
        DeValue::Float(f) => {
            let parsed: f64 = f.as_str().parse().map_err(|_| {
                ConvertError::new(format!(
                    "Invalid TOML float at '{}': {}",
                    path_string(path),
                    f.as_str()
                ))
            })?;
            serde_json::Number::from_f64(parsed)
                .map(Value::Number)
                .ok_or_else(|| {
                    ConvertError::new(format!(
                        "TOML float '{}' at '{}' is non-finite and cannot be represented in JSON or YAML",
                        f.as_str(),
                        path_string(path)
                    ))
                })
        }
        // JSON/YAML have no datetime type: RFC 3339 string form.
        DeValue::Datetime(dt) => Ok(Value::String(dt.to_string())),
        DeValue::Array(a) => dearray_to_value(a, path),
        DeValue::Table(t) => detable_to_value(t, path),
    }
}

// ------------------------------------------------------------------ writing

fn to_json_string(value: &Value) -> Result<String, ConvertError> {
    // serde_json pretty printing: 2-space indent, non-ASCII written literally.
    let mut text = serde_json::to_string_pretty(value)
        .map_err(|e| ConvertError::with_detail("Failed to serialize JSON", e.to_string()))?;
    text.push('\n');
    Ok(text)
}

fn to_yaml_string(value: &Value) -> Result<String, ConvertError> {
    // Defaults: block style, 2-space indent, insertion order (no sorting).
    // Bool-like strings ("no", "on", ...) are auto-quoted so they stay strings.
    serde_saphyr::to_string(value)
        .map_err(|e| ConvertError::with_detail("Failed to serialize YAML", e.to_string()))
}

fn to_toml_string(value: &Value) -> Result<String, ConvertError> {
    let root = value.as_object().ok_or_else(|| {
        ConvertError::new(format!(
            "TOML requires a table (object) at the document root, but the input root is {}",
            json_type_name(value)
        ))
    })?;
    let mut out = String::new();
    emit_table(&mut out, root, &mut Vec::new())?;
    Ok(out)
}

/// True for arrays that should be emitted as `[[key]]` sections.
fn is_array_of_tables(value: &Value) -> bool {
    match value {
        Value::Array(items) => !items.is_empty() && items.iter().all(Value::is_object),
        _ => false,
    }
}

/// Emit one table level: `key = value` lines first (TOML requires plain keys
/// before sub-table headers), then `[table]` / `[[array-of-tables]]` sections,
/// each group in insertion order.
fn emit_table(
    out: &mut String,
    table: &serde_json::Map<String, Value>,
    path: &mut Vec<String>,
) -> Result<(), ConvertError> {
    for (key, val) in table {
        if val.is_object() || is_array_of_tables(val) {
            continue;
        }
        path.push(key.clone());
        let rendered = emit_inline(val, path)?;
        path.pop();
        let _ = writeln!(out, "{} = {rendered}", toml_key(key));
    }

    for (key, val) in table {
        path.push(key.clone());
        if let Value::Object(sub) = val {
            if !out.is_empty() {
                out.push('\n');
            }
            let _ = writeln!(out, "[{}]", header_path(path));
            emit_table(out, sub, path)?;
        } else if is_array_of_tables(val) {
            let items = val.as_array().expect("checked: array of tables");
            for (index, item) in items.iter().enumerate() {
                let sub = item.as_object().expect("checked: array of tables");
                if !out.is_empty() {
                    out.push('\n');
                }
                let _ = writeln!(out, "[[{}]]", header_path(path));
                path.push(format!("[{index}]"));
                emit_table(out, sub, path)?;
                path.pop();
            }
        }
        path.pop();
    }
    Ok(())
}

/// Render a value in inline position (`key = ...`, array element, inline table).
fn emit_inline(value: &Value, path: &mut Vec<String>) -> Result<String, ConvertError> {
    match value {
        Value::Null => Err(ConvertError::new(format!(
            "TOML cannot represent null (at '{}'); remove the key or give it a value",
            path_string(path)
        ))),
        Value::Bool(b) => Ok(b.to_string()),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.to_string())
            } else if n.is_u64() {
                Err(ConvertError::new(format!(
                    "Integer {n} at '{}' exceeds the TOML integer range (max {})",
                    path_string(path),
                    i64::MAX
                )))
            } else {
                // serde_json floats are always finite; its Display form
                // (ryu) always carries a fraction or exponent — valid TOML.
                Ok(n.to_string())
            }
        }
        Value::String(s) => Ok(toml_escape(s)),
        Value::Array(items) => {
            let mut parts = Vec::with_capacity(items.len());
            for (index, item) in items.iter().enumerate() {
                path.push(format!("[{index}]"));
                parts.push(emit_inline(item, path)?);
                path.pop();
            }
            Ok(format!("[{}]", parts.join(", ")))
        }
        Value::Object(map) => {
            // Inline table — reached inside mixed arrays.
            let mut parts = Vec::with_capacity(map.len());
            for (key, val) in map {
                path.push(key.clone());
                let rendered = emit_inline(val, path)?;
                path.pop();
                parts.push(format!("{} = {rendered}", toml_key(key)));
            }
            Ok(format!("{{ {} }}", parts.join(", ")))
        }
    }
}

/// A key as it appears in TOML: bare when possible, basic-string otherwise.
fn toml_key(key: &str) -> String {
    let bare = !key.is_empty()
        && key
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-');
    if bare {
        key.to_string()
    } else {
        toml_escape(key)
    }
}

/// Dotted header path for `[section]` headers (index segments never appear:
/// array-of-tables headers repeat the array key).
fn header_path(path: &[String]) -> String {
    path.iter()
        .filter(|seg| !seg.starts_with('['))
        .map(|seg| toml_key(seg))
        .collect::<Vec<_>>()
        .join(".")
}

fn toml_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\t' => out.push_str("\\t"),
            '\r' => out.push_str("\\r"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0c}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 || c == '\u{7f}' => {
                let _ = write!(out, "\\u{:04X}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

// ------------------------------------------------------------------ helpers

/// Human-readable key path like `database.password` or `servers[1].host`.
fn path_string(path: &[String]) -> String {
    let mut out = String::new();
    for seg in path {
        if seg.starts_with('[') || out.is_empty() {
            out.push_str(seg);
        } else {
            out.push('.');
            out.push_str(seg);
        }
    }
    if out.is_empty() {
        "(root)".to_string()
    } else {
        out
    }
}

fn json_type_name(value: &Value) -> &'static str {
    match value {
        Value::Null => "null",
        Value::Bool(_) => "a boolean",
        Value::Number(_) => "a number",
        Value::String(_) => "a string",
        Value::Array(_) => "an array",
        Value::Object(_) => "an object",
    }
}
