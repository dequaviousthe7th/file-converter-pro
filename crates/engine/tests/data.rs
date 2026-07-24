//! Integration tests for the data domain (csv/tsv/xlsx/json tables) —
//! exercised through the public `convert::convert` dispatch (plan Task 4).

use std::fs;
use std::path::{Path, PathBuf};

use calamine::{open_workbook, Reader, Xlsx};
use fcp_engine::convert::{convert, ConversionRequest};
use fcp_engine::error::ConvertError;
use fcp_engine::job::CancelToken;
use fcp_engine::options::{ConvertOptions, Sidecars};

fn run(
    dir: &Path,
    file_name: &str,
    content: &[u8],
    target: &str,
) -> Result<Vec<PathBuf>, ConvertError> {
    let input = dir.join(file_name);
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
        &|_p, _m| {},
    )
}

fn run_path(dir: &Path, input: PathBuf, target: &str) -> Result<Vec<PathBuf>, ConvertError> {
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
        &|_p, _m| {},
    )
}

#[test]
fn csv_to_json_records_orient_two_space_indent() {
    let dir = tempfile::tempdir().unwrap();
    let outs = run(dir.path(), "in.csv", b"a,b\n1,x\n2,y\n", "json").unwrap();
    assert_eq!(outs.len(), 1);
    assert_eq!(
        outs[0].file_name().unwrap().to_str().unwrap(),
        "in_converted.json"
    );
    let text = fs::read_to_string(&outs[0]).unwrap();
    let expected = "[\n  {\n    \"a\": \"1\",\n    \"b\": \"x\"\n  },\n  {\n    \"a\": \"2\",\n    \"b\": \"y\"\n  }\n]";
    assert_eq!(text, expected);
}

#[test]
fn csv_to_xlsx_then_calamine_reads_back_same_cells() {
    let dir = tempfile::tempdir().unwrap();
    let outs = run(dir.path(), "in.csv", b"a,b\n1,x\n2,y\n", "xlsx").unwrap();
    let mut wb: Xlsx<_> = open_workbook(&outs[0]).unwrap();
    let range = wb.worksheet_range_at(0).unwrap().unwrap();
    let cell = |r: u32, c: u32| range.get_value((r, c)).unwrap().to_string();
    assert_eq!(cell(0, 0), "a");
    assert_eq!(cell(0, 1), "b");
    assert_eq!(cell(1, 0), "1");
    assert_eq!(cell(1, 1), "x");
    assert_eq!(cell(2, 0), "2");
    assert_eq!(cell(2, 1), "y");
}

#[test]
fn csv_to_xlsx_to_csv_round_trip() {
    let dir = tempfile::tempdir().unwrap();
    let original = "a,b\n1,x\n2,y\n";
    let xlsx = run(dir.path(), "in.csv", original.as_bytes(), "xlsx").unwrap();
    let csv_out = run_path(dir.path(), xlsx[0].clone(), "csv").unwrap();
    assert_eq!(fs::read_to_string(&csv_out[0]).unwrap(), original);
}

#[test]
fn json_array_to_csv_headers_union_ordered_by_first_appearance() {
    let dir = tempfile::tempdir().unwrap();
    let json = br#"[{"b":"1","a":"2"},{"c":"3","a":"4"}]"#;
    let outs = run(dir.path(), "in.json", json, "csv").unwrap();
    let text = fs::read_to_string(&outs[0]).unwrap();
    assert_eq!(text, "b,a,c\n1,2,\n,4,3\n");
}

#[test]
fn csv_to_tsv_uses_tab_delimiter() {
    let dir = tempfile::tempdir().unwrap();
    let outs = run(dir.path(), "in.csv", b"a,b\n1,x\n", "tsv").unwrap();
    let text = fs::read_to_string(&outs[0]).unwrap();
    assert_eq!(text, "a\tb\n1\tx\n");
}

#[test]
fn tsv_to_json_reads_tab_delimiter() {
    let dir = tempfile::tempdir().unwrap();
    let outs = run(dir.path(), "in.tsv", b"a\tb\n1\tx\n", "json").unwrap();
    let parsed: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&outs[0]).unwrap()).unwrap();
    assert_eq!(parsed, serde_json::json!([{"a": "1", "b": "x"}]));
}

#[test]
fn xlsx_to_html_produces_v2_styled_page() {
    let dir = tempfile::tempdir().unwrap();
    let xlsx = run(dir.path(), "in.csv", b"a,b\n1,x\n", "xlsx").unwrap();
    let outs = run_path(dir.path(), xlsx[0].clone(), "html").unwrap();
    let html = fs::read_to_string(&outs[0]).unwrap();
    assert!(html.contains("<table"), "missing <table: {html}");
    assert!(html.contains("#4a90d9"), "missing header color: {html}");
    assert!(
        html.contains("nth-child(even)"),
        "missing zebra rows: {html}"
    );
    assert!(
        html.contains("border-collapse"),
        "missing border-collapse: {html}"
    );
    assert!(html.contains("<th>a</th>"), "missing header cell: {html}");
    assert!(html.contains("<td>x</td>"), "missing data cell: {html}");
}

#[test]
fn html_output_escapes_cell_content() {
    let dir = tempfile::tempdir().unwrap();
    let outs = run(dir.path(), "in.csv", b"a\n\"<b>&\"\n", "html").unwrap();
    let html = fs::read_to_string(&outs[0]).unwrap();
    assert!(html.contains("&lt;b&gt;&amp;"), "cell not escaped: {html}");
}

#[test]
fn json_nested_values_become_compact_json_strings() {
    let dir = tempfile::tempdir().unwrap();
    let json = br#"[{"a":{"x":1},"b":[1,2],"c":"s"}]"#;
    let outs = run(dir.path(), "in.json", json, "csv").unwrap();
    let mut rdr = csv::Reader::from_path(&outs[0]).unwrap();
    let headers = rdr.headers().unwrap().clone();
    assert_eq!(headers.iter().collect::<Vec<_>>(), vec!["a", "b", "c"]);
    let row = rdr.records().next().unwrap().unwrap();
    assert_eq!(&row[0], r#"{"x":1}"#);
    assert_eq!(&row[1], "[1,2]");
    assert_eq!(&row[2], "s");
}

#[test]
fn json_scalar_null_bool_number_cells() {
    let dir = tempfile::tempdir().unwrap();
    let json = br#"[{"n":1.5,"b":true,"z":null}]"#;
    let outs = run(dir.path(), "in.json", json, "csv").unwrap();
    assert_eq!(fs::read_to_string(&outs[0]).unwrap(), "n,b,z\n1.5,true,\n");
}

#[test]
fn json_dict_root_uses_first_nonempty_array_of_objects() {
    let dir = tempfile::tempdir().unwrap();
    let json = br#"{"meta":{"x":1},"count":2,"items":[{"a":"1"},{"a":"2"}],"other":[{"b":"9"}]}"#;
    let outs = run(dir.path(), "in.json", json, "csv").unwrap();
    assert_eq!(fs::read_to_string(&outs[0]).unwrap(), "a\n1\n2\n");
}

#[test]
fn json_dict_root_without_tabular_value_errors() {
    let dir = tempfile::tempdir().unwrap();
    let json = br#"{"meta":{"x":1},"count":2,"empty":[]}"#;
    let err = run(dir.path(), "in.json", json, "csv").unwrap_err();
    assert!(
        err.message.contains("array of objects"),
        "unexpected message: {}",
        err.message
    );
}

#[test]
fn json_scalar_root_errors() {
    let dir = tempfile::tempdir().unwrap();
    let err = run(dir.path(), "in.json", b"42", "csv").unwrap_err();
    assert!(
        err.message.contains("not supported for tabular conversion"),
        "unexpected message: {}",
        err.message
    );
}

#[test]
fn json_empty_array_errors_no_data_rows() {
    let dir = tempfile::tempdir().unwrap();
    let err = run(dir.path(), "in.json", b"[]", "csv").unwrap_err();
    assert_eq!(err.message, "No data rows found");
}

#[test]
fn invalid_json_errors() {
    let dir = tempfile::tempdir().unwrap();
    let err = run(dir.path(), "in.json", b"not json", "csv").unwrap_err();
    assert_eq!(err.message, "Invalid JSON input");
    assert!(err.detail.is_some());
}

#[test]
fn empty_csv_errors_no_data_rows() {
    let dir = tempfile::tempdir().unwrap();
    // header-only
    let err = run(dir.path(), "hdr.csv", b"a,b\n", "json").unwrap_err();
    assert_eq!(err.message, "No data rows found");
    // fully empty
    let err = run(dir.path(), "empty.csv", b"", "json").unwrap_err();
    assert_eq!(err.message, "No data rows found");
}

#[test]
fn short_csv_rows_padded_with_empty_cells() {
    let dir = tempfile::tempdir().unwrap();
    let outs = run(dir.path(), "in.csv", b"a,b\n1\n", "json").unwrap();
    let parsed: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&outs[0]).unwrap()).unwrap();
    assert_eq!(parsed, serde_json::json!([{"a": "1", "b": ""}]));
}

#[test]
fn non_ascii_preserved_in_json_output() {
    let dir = tempfile::tempdir().unwrap();
    let outs = run(
        dir.path(),
        "in.csv",
        "name\n\u{65e5}\u{672c}\u{8a9e}\n".as_bytes(),
        "json",
    )
    .unwrap();
    let text = fs::read_to_string(&outs[0]).unwrap();
    assert!(
        text.contains("\u{65e5}\u{672c}\u{8a9e}"),
        "non-ascii escaped: {text}"
    );
    assert!(!text.contains("\\u"), "found unicode escapes: {text}");
}

#[test]
fn invalid_utf8_csv_read_lossy() {
    let dir = tempfile::tempdir().unwrap();
    let outs = run(dir.path(), "in.csv", b"a\n\xff\xfe\n", "json").unwrap();
    let parsed: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&outs[0]).unwrap()).unwrap();
    assert_eq!(parsed, serde_json::json!([{"a": "\u{fffd}\u{fffd}"}]));
}

#[test]
fn numeric_xlsx_cells_preserve_display() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("nums.xlsx");
    let mut wb = rust_xlsxwriter::Workbook::new();
    let ws = wb.add_worksheet();
    ws.write_string(0, 0, "n").unwrap();
    ws.write_string(0, 1, "b").unwrap();
    ws.write_number(1, 0, 2.0).unwrap();
    ws.write_boolean(1, 1, true).unwrap();
    ws.write_number(2, 0, 2.5).unwrap();
    ws.write_boolean(2, 1, false).unwrap();
    wb.save(&path).unwrap();
    let outs = run_path(dir.path(), path, "csv").unwrap();
    assert_eq!(
        fs::read_to_string(&outs[0]).unwrap(),
        "n,b\n2,TRUE\n2.5,FALSE\n"
    );
}

#[test]
fn json_to_tsv_and_back_round_trip() {
    let dir = tempfile::tempdir().unwrap();
    let json = br#"[{"a":"1","b":"x"},{"a":"2","b":"y"}]"#;
    let tsv = run(dir.path(), "in.json", json, "tsv").unwrap();
    assert_eq!(fs::read_to_string(&tsv[0]).unwrap(), "a\tb\n1\tx\n2\ty\n");
    let back = run_path(dir.path(), tsv[0].clone(), "json").unwrap();
    let parsed: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&back[0]).unwrap()).unwrap();
    assert_eq!(
        parsed,
        serde_json::json!([{"a": "1", "b": "x"}, {"a": "2", "b": "y"}])
    );
}

#[test]
fn json_array_with_non_object_item_errors() {
    let dir = tempfile::tempdir().unwrap();
    let err = run(dir.path(), "in.json", br#"[{"a":"1"},5]"#, "csv").unwrap_err();
    assert!(
        err.message.contains("objects"),
        "unexpected message: {}",
        err.message
    );
}

#[test]
fn quoted_csv_fields_survive_to_xlsx_and_back() {
    let dir = tempfile::tempdir().unwrap();
    let original = "a,b\n\"1,5\",\"line\nbreak\"\n";
    let xlsx = run(dir.path(), "in.csv", original.as_bytes(), "xlsx").unwrap();
    let back = run_path(dir.path(), xlsx[0].clone(), "csv").unwrap();
    assert_eq!(fs::read_to_string(&back[0]).unwrap(), original);
}
