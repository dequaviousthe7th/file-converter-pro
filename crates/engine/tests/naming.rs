use std::fs;

use fcp_engine::convert::unique_output_path;

#[test]
fn no_collision_uses_converted_suffix() {
    let dir = tempfile::tempdir().unwrap();
    let path = unique_output_path(dir.path(), "photo", "jpg");
    assert_eq!(path, dir.path().join("photo_converted.jpg"));
}

#[test]
fn collision_appends_counter() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(dir.path().join("photo_converted.jpg"), b"x").unwrap();

    let path = unique_output_path(dir.path(), "photo", "jpg");
    assert_eq!(path, dir.path().join("photo_converted (1).jpg"));

    fs::write(&path, b"x").unwrap();
    let path2 = unique_output_path(dir.path(), "photo", "jpg");
    assert_eq!(path2, dir.path().join("photo_converted (2).jpg"));
}

#[test]
fn counter_fills_first_free_slot() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(dir.path().join("doc_converted.pdf"), b"x").unwrap();
    fs::write(dir.path().join("doc_converted (1).pdf"), b"x").unwrap();
    fs::write(dir.path().join("doc_converted (2).pdf"), b"x").unwrap();

    let path = unique_output_path(dir.path(), "doc", "pdf");
    assert_eq!(path, dir.path().join("doc_converted (3).pdf"));
}

#[test]
fn stems_with_spaces_and_dots_are_preserved() {
    let dir = tempfile::tempdir().unwrap();
    let path = unique_output_path(dir.path(), "my file v1.2", "png");
    assert_eq!(path, dir.path().join("my file v1.2_converted.png"));
}
