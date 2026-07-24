//! Integration tests for the config hub (json/yaml/toml via serde_json::Value).

use std::fs;
use std::path::{Path, PathBuf};

use fcp_engine::convert::{convert, ConversionRequest};
use fcp_engine::error::ConvertError;
use fcp_engine::job::CancelToken;
use fcp_engine::options::{ConvertOptions, Sidecars};

fn run_conv(
    dir: &Path,
    name: &str,
    content: &str,
    target: &str,
) -> Result<Vec<PathBuf>, ConvertError> {
    let input = dir.join(name);
    fs::write(&input, content).unwrap();
    let req = ConversionRequest {
        input,
        target: target.to_string(),
        output_dir: dir.to_path_buf(),
        options: ConvertOptions::default(),
    };
    convert(
        &req,
        &Sidecars::default(),
        &CancelToken::default(),
        &|_, _| {},
    )
}

/// Run a conversion that must succeed and return the produced text.
fn convert_ok(dir: &Path, name: &str, content: &str, target: &str) -> String {
    let outputs = run_conv(dir, name, content, target)
        .unwrap_or_else(|e| panic!("conversion {name} -> {target} failed: {}", e.message));
    assert_eq!(outputs.len(), 1, "expected exactly one output");
    fs::read_to_string(&outputs[0]).unwrap()
}

// ---------------------------------------------------------------- yaml -> json

#[test]
fn yaml_to_json_preserves_key_order() {
    let dir = tempfile::tempdir().unwrap();
    let out = convert_ok(
        dir.path(),
        "in.yaml",
        "zebra: 1\nalpha: 2\nmike: 3\n",
        "json",
    );
    let z = out.find("\"zebra\"").expect("zebra missing");
    let a = out.find("\"alpha\"").expect("alpha missing");
    let m = out.find("\"mike\"").expect("mike missing");
    assert!(z < a && a < m, "key order not preserved: {out}");
}

#[test]
fn json_output_uses_two_space_indent_and_keeps_non_ascii() {
    let dir = tempfile::tempdir().unwrap();
    let out = convert_ok(
        dir.path(),
        "in.yaml",
        "greeting: héllo ✓\nnested:\n  inner: 1\n",
        "json",
    );
    // 2-space indent at depth 1.
    assert!(
        out.contains("\n  \"greeting\""),
        "expected two-space indent: {out}"
    );
    // Non-ASCII must be written literally, not \u-escaped.
    assert!(out.contains("héllo ✓"), "non-ascii not preserved: {out}");
    assert!(!out.contains("\\u"), "unexpected unicode escaping: {out}");
}

#[test]
fn yaml_bool_like_scalars_stay_strings_yaml_12() {
    let dir = tempfile::tempdir().unwrap();
    let out = convert_ok(
        dir.path(),
        "in.yaml",
        "a: no\nb: on\nc: yes\nd: true\ne: false\n",
        "json",
    );
    let v: serde_json::Value = serde_json::from_str(&out).unwrap();
    assert_eq!(v["a"], serde_json::Value::String("no".into()));
    assert_eq!(v["b"], serde_json::Value::String("on".into()));
    assert_eq!(v["c"], serde_json::Value::String("yes".into()));
    assert_eq!(v["d"], serde_json::Value::Bool(true));
    assert_eq!(v["e"], serde_json::Value::Bool(false));
}

#[test]
fn yaml_non_finite_scalar_round_trips_as_string() {
    let dir = tempfile::tempdir().unwrap();
    // serde_json::Value cannot hold NaN; the YAML deserializer yields the
    // canonical string instead — assert no panic and a string result.
    let out = convert_ok(dir.path(), "in.yaml", "x: .nan\ny: .inf\n", "json");
    let v: serde_json::Value = serde_json::from_str(&out).unwrap();
    assert_eq!(v["x"], serde_json::Value::String(".nan".into()));
    assert_eq!(v["y"], serde_json::Value::String(".inf".into()));
}

// ---------------------------------------------------------------- json -> yaml

#[test]
fn json_to_yaml_block_style_no_key_sorting() {
    let dir = tempfile::tempdir().unwrap();
    let out = convert_ok(
        dir.path(),
        "in.json",
        r#"{"zulu": {"beta": 2, "alpha": 1}, "apple": [1, 2], "mike": "x"}"#,
        "yaml",
    );
    // Block style: no flow braces for non-empty maps.
    assert!(!out.contains('{'), "expected block style, got: {out}");
    assert!(out.contains("- 1"), "expected block sequence, got: {out}");
    // Insertion order preserved (no alphabetical sorting).
    let z = out.find("zulu").unwrap();
    let b = out.find("beta").unwrap();
    let a = out.find("alpha").unwrap();
    let ap = out.find("apple").unwrap();
    let m = out.find("mike").unwrap();
    assert!(z < b && b < a && a < ap && ap < m, "order changed: {out}");
}

#[test]
fn json_to_yaml_preserves_unicode() {
    let dir = tempfile::tempdir().unwrap();
    let out = convert_ok(
        dir.path(),
        "in.json",
        r#"{"name": "Zoë 日本語 🚀", "note": "ünïcode"}"#,
        "yaml",
    );
    // Round-trip through a YAML parser: exact strings survive.
    let v: serde_json::Value = serde_saphyr::from_str(&out).unwrap();
    assert_eq!(v["name"], serde_json::Value::String("Zoë 日本語 🚀".into()));
    assert_eq!(v["note"], serde_json::Value::String("ünïcode".into()));
}

#[test]
fn json_to_yaml_bool_like_string_survives_round_trip() {
    let dir = tempfile::tempdir().unwrap();
    let out = convert_ok(dir.path(), "in.json", r#"{"answer": "no"}"#, "yaml");
    // The emitted YAML must keep "no" a string (quoted), not turn it into a bool.
    let v: serde_json::Value = serde_saphyr::from_str(&out).unwrap();
    assert_eq!(v["answer"], serde_json::Value::String("no".into()));
}

// ---------------------------------------------------------------- json -> toml

#[test]
fn json_null_to_toml_errors_with_key_path() {
    let dir = tempfile::tempdir().unwrap();
    let err = run_conv(
        dir.path(),
        "in.json",
        r#"{"database": {"password": null}}"#,
        "toml",
    )
    .unwrap_err();
    assert!(
        err.message.contains("null"),
        "message should mention null: {}",
        err.message
    );
    assert!(
        err.message.contains("database.password"),
        "message should name the key path: {}",
        err.message
    );
}

#[test]
fn json_array_root_to_toml_errors() {
    let dir = tempfile::tempdir().unwrap();
    let err = run_conv(dir.path(), "in.json", "[1, 2, 3]", "toml").unwrap_err();
    assert!(
        err.message.contains("root") && err.message.contains("array"),
        "unclear error: {}",
        err.message
    );
}

#[test]
fn json_scalar_root_to_toml_errors() {
    let dir = tempfile::tempdir().unwrap();
    let err = run_conv(dir.path(), "in.json", "42", "toml").unwrap_err();
    assert!(
        err.message.contains("root"),
        "unclear error: {}",
        err.message
    );
}

#[test]
fn json_u64_overflow_to_toml_errors() {
    let dir = tempfile::tempdir().unwrap();
    // u64::MAX fits JSON but not TOML's i64 integers.
    let err = run_conv(
        dir.path(),
        "in.json",
        r#"{"big": 18446744073709551615}"#,
        "toml",
    )
    .unwrap_err();
    assert!(
        err.message.contains("big"),
        "message should name the key path: {}",
        err.message
    );
    assert!(
        err.message.to_lowercase().contains("integer"),
        "message should explain the integer range problem: {}",
        err.message
    );
}

#[test]
fn json_to_toml_structure_order_and_values() {
    let dir = tempfile::tempdir().unwrap();
    let out = convert_ok(
        dir.path(),
        "in.json",
        r#"{
            "title": "Test",
            "count": 42,
            "ratio": 3.5,
            "enabled": true,
            "tags": ["a", "b"],
            "weird key!": "quoted",
            "server": {"host": "localhost", "port": 8080},
            "points": [{"x": 1}, {"x": 2}]
        }"#,
        "toml",
    );
    // Parses as valid TOML with the same values.
    let v: toml::Table = toml::from_str(&out).unwrap();
    assert_eq!(v["title"].as_str(), Some("Test"));
    assert_eq!(v["count"].as_integer(), Some(42));
    assert_eq!(v["ratio"].as_float(), Some(3.5));
    assert_eq!(v["enabled"].as_bool(), Some(true));
    assert_eq!(v["tags"][0].as_str(), Some("a"));
    assert_eq!(v["weird key!"].as_str(), Some("quoted"));
    assert_eq!(v["server"]["port"].as_integer(), Some(8080));
    assert_eq!(v["points"][1]["x"].as_integer(), Some(2));
    // Simple keys come before table sections; sections keep insertion order.
    let title = out.find("title").unwrap();
    let server = out.find("[server]").expect("expected [server] section");
    let points = out
        .find("[[points]]")
        .expect("expected [[points]] sections");
    assert!(title < server && server < points, "section order: {out}");
}

#[test]
fn json_to_toml_escapes_strings() {
    let dir = tempfile::tempdir().unwrap();
    let out = convert_ok(
        dir.path(),
        "in.json",
        r#"{"text": "line1\nline2\t\"quoted\" \\ back", "emoji": "héllo 🚀"}"#,
        "toml",
    );
    let v: toml::Table = toml::from_str(&out).unwrap();
    assert_eq!(v["text"].as_str(), Some("line1\nline2\t\"quoted\" \\ back"));
    assert_eq!(v["emoji"].as_str(), Some("héllo 🚀"));
}

// ---------------------------------------------------------------- toml -> json/yaml

#[test]
fn toml_datetime_to_json_is_rfc3339_string() {
    let dir = tempfile::tempdir().unwrap();
    let out = convert_ok(
        dir.path(),
        "in.toml",
        "created = 1979-05-27T07:32:00Z\n",
        "json",
    );
    let v: serde_json::Value = serde_json::from_str(&out).unwrap();
    assert_eq!(
        v["created"],
        serde_json::Value::String("1979-05-27T07:32:00Z".into())
    );
}

#[test]
fn toml_datetime_to_yaml_is_rfc3339_string() {
    let dir = tempfile::tempdir().unwrap();
    let out = convert_ok(
        dir.path(),
        "in.toml",
        "created = 1979-05-27T07:32:00Z\n",
        "yaml",
    );
    let v: serde_json::Value = serde_saphyr::from_str(&out).unwrap();
    assert_eq!(
        v["created"],
        serde_json::Value::String("1979-05-27T07:32:00Z".into())
    );
}

#[test]
fn toml_non_finite_float_to_json_errors() {
    let dir = tempfile::tempdir().unwrap();
    for (content, needle) in [("v = nan\n", "v"), ("w = inf\n", "w")] {
        let err = run_conv(dir.path(), "in.toml", content, "json").unwrap_err();
        assert!(
            err.message.contains(needle),
            "message should name the key path: {}",
            err.message
        );
        assert!(
            err.message.to_lowercase().contains("non-finite"),
            "message should explain the non-finite problem: {}",
            err.message
        );
    }
}

#[test]
fn toml_to_json_preserves_source_order() {
    let dir = tempfile::tempdir().unwrap();
    // BTreeMap-backed toml tables would sort alphabetically; source spans must win.
    let out = convert_ok(
        dir.path(),
        "in.toml",
        "zeta = 1\nalpha = 2\n\n[zebra]\nx = 1\n\n[apple]\ny = 2\n",
        "json",
    );
    let zeta = out.find("\"zeta\"").unwrap();
    let alpha = out.find("\"alpha\"").unwrap();
    let zebra = out.find("\"zebra\"").unwrap();
    let apple = out.find("\"apple\"").unwrap();
    assert!(
        zeta < alpha && alpha < zebra && zebra < apple,
        "source order not preserved: {out}"
    );
}

#[test]
fn toml_to_yaml_values_and_order() {
    let dir = tempfile::tempdir().unwrap();
    let out = convert_ok(
        dir.path(),
        "in.toml",
        "name = \"app\"\nport = 8080\n\n[limits]\nmax = 10\n",
        "yaml",
    );
    let v: serde_json::Value = serde_saphyr::from_str(&out).unwrap();
    assert_eq!(v["name"], serde_json::Value::String("app".into()));
    assert_eq!(v["port"], serde_json::Value::from(8080));
    assert_eq!(v["limits"]["max"], serde_json::Value::from(10));
    assert!(out.find("name").unwrap() < out.find("port").unwrap());
    assert!(out.find("port").unwrap() < out.find("limits").unwrap());
}

// ---------------------------------------------------------------- yaml -> toml

#[test]
fn yaml_to_toml_nested_map_becomes_section() {
    let dir = tempfile::tempdir().unwrap();
    let out = convert_ok(
        dir.path(),
        "in.yaml",
        "name: app\nnested:\n  key: value\n",
        "toml",
    );
    let v: toml::Table = toml::from_str(&out).unwrap();
    assert_eq!(v["name"].as_str(), Some("app"));
    assert_eq!(v["nested"]["key"].as_str(), Some("value"));
    assert!(out.contains("[nested]"), "expected a table section: {out}");
}

// ---------------------------------------------------------------- errors + naming

#[test]
fn invalid_json_input_errors_clearly() {
    let dir = tempfile::tempdir().unwrap();
    let err = run_conv(dir.path(), "in.json", "{not json", "yaml").unwrap_err();
    assert!(
        err.message.contains("JSON"),
        "unclear error: {}",
        err.message
    );
}

#[test]
fn invalid_toml_input_errors_clearly() {
    let dir = tempfile::tempdir().unwrap();
    let err = run_conv(dir.path(), "in.toml", "dummy", "json").unwrap_err();
    assert!(
        err.message.contains("TOML"),
        "unclear error: {}",
        err.message
    );
}

#[test]
fn output_uses_converted_suffix_and_alias_extension() {
    let dir = tempfile::tempdir().unwrap();
    // yml alias input normalizes to yaml; output name follows the v2 contract.
    let outputs = run_conv(dir.path(), "settings.yml", "a: 1\n", "json").unwrap();
    assert_eq!(outputs.len(), 1);
    assert_eq!(
        outputs[0].file_name().unwrap().to_str().unwrap(),
        "settings_converted.json"
    );
}
