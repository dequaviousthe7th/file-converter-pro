use fcp_engine::registry::{
    format_for, formats, is_supported, normalize_ext, total_pairs, Category,
};

#[test]
fn pdf_has_six_targets_in_order() {
    let pdf = format_for("pdf").expect("pdf must be registered");
    assert_eq!(pdf.targets, ["docx", "txt", "md", "png", "jpg", "html"]);
}

#[test]
fn every_target_is_a_known_format() {
    for f in formats() {
        for t in f.targets {
            assert!(
                is_supported(t),
                "target `{t}` of `{}` is not a registered format",
                f.ext
            );
        }
    }
}

#[test]
fn no_format_targets_itself() {
    for f in formats() {
        assert!(
            !f.targets.contains(&f.ext),
            "`{}` lists itself as a target",
            f.ext
        );
    }
}

#[test]
fn registry_stores_canonical_extensions_only() {
    for alias in ["jpeg", "tif", "yml", "heif", "htm"] {
        assert!(
            !formats().iter().any(|f| f.ext == alias),
            "alias `{alias}` must not be a registry entry"
        );
    }
}

#[test]
fn aliases_normalize() {
    assert_eq!(normalize_ext("jpeg"), "jpg");
    assert_eq!(normalize_ext("tif"), "tiff");
    assert_eq!(normalize_ext("yml"), "yaml");
    assert_eq!(normalize_ext("heif"), "heic");
    assert_eq!(normalize_ext("htm"), "html");
    // canonical inputs pass through unchanged
    assert_eq!(normalize_ext("jpg"), "jpg");
    assert_eq!(normalize_ext("png"), "png");
    // case-insensitive
    assert_eq!(normalize_ext("JPEG"), "jpg");
    assert_eq!(normalize_ext("TIF"), "tiff");
    assert_eq!(normalize_ext("PNG"), "png");
}

#[test]
fn is_supported_is_case_insensitive() {
    assert!(is_supported("JPEG"));
    assert!(is_supported("PnG"));
    assert!(is_supported("Heif"));
    assert!(is_supported("YML"));
    assert!(!is_supported("xyz"));
    assert!(!is_supported(""));
}

#[test]
fn format_for_resolves_aliases_and_case() {
    assert_eq!(format_for("JPEG").unwrap().ext, "jpg");
    assert_eq!(format_for("tif").unwrap().ext, "tiff");
    assert_eq!(format_for("yml").unwrap().ext, "yaml");
    assert!(format_for("nope").is_none());
}

#[test]
fn format_and_pair_counts_match_matrix() {
    // 7 documents + 9 images + 7 audio + 5 video + 4 data + 2 config
    assert_eq!(formats().len(), 34);
    // documents 27 + images 50 + audio 36 + video 25 + data 16 + config 4
    assert_eq!(total_pairs(), 158);
}

#[test]
fn per_category_pair_counts() {
    let count = |cat: Category| -> usize {
        formats()
            .iter()
            .filter(|f| f.category == cat)
            .map(|f| f.targets.len())
            .sum()
    };
    assert_eq!(count(Category::Documents), 27);
    assert_eq!(count(Category::Images), 50);
    assert_eq!(count(Category::Audio), 36);
    assert_eq!(count(Category::Video), 25);
    assert_eq!(count(Category::Data), 16);
    assert_eq!(count(Category::Config), 4);
}

#[test]
fn icons_match_v2() {
    let icon = |ext: &str| format_for(ext).unwrap().icon;
    assert_eq!(icon("pdf"), "\u{1F4C4}"); // 📄
    assert_eq!(icon("docx"), "\u{1F4DD}"); // 📝
    assert_eq!(icon("md"), "\u{1F4D1}"); // 📑
    assert_eq!(icon("txt"), "\u{1F4C3}"); // 📃
    assert_eq!(icon("html"), "\u{1F310}"); // 🌐
    assert_eq!(icon("rtf"), "\u{1F4C4}"); // 📄
    assert_eq!(icon("epub"), "\u{1F4DA}"); // 📚
    assert_eq!(icon("png"), "\u{1F5BC}\u{FE0F}"); // 🖼️
    assert_eq!(icon("mp3"), "\u{1F3B5}"); // 🎵
    assert_eq!(icon("mp4"), "\u{1F3AC}"); // 🎬
    assert_eq!(icon("csv"), "\u{1F4CA}"); // 📊
    assert_eq!(icon("yaml"), "\u{2699}\u{FE0F}"); // ⚙️
}

#[test]
fn spot_check_categories() {
    assert_eq!(format_for("epub").unwrap().category, Category::Documents);
    assert_eq!(format_for("heic").unwrap().category, Category::Images);
    assert_eq!(format_for("wma").unwrap().category, Category::Audio);
    assert_eq!(format_for("webm").unwrap().category, Category::Video);
    assert_eq!(format_for("tsv").unwrap().category, Category::Data);
    assert_eq!(format_for("toml").unwrap().category, Category::Config);
}

#[test]
fn spot_check_target_lists() {
    let targets = |ext: &str| format_for(ext).unwrap().targets;
    assert_eq!(targets("epub"), ["pdf", "txt", "docx"]);
    assert_eq!(
        targets("heic"),
        ["png", "jpg", "webp", "bmp", "pdf", "tiff"]
    );
    assert_eq!(targets("svg"), ["png", "jpg", "webp", "pdf"]);
    assert_eq!(targets("ico"), ["png", "jpg", "bmp"]);
    assert_eq!(targets("mp3"), ["wav", "flac", "ogg", "aac", "m4a", "wma"]);
    assert_eq!(targets("webm"), ["mp4", "avi", "mkv", "mov", "gif"]);
    assert_eq!(targets("json"), ["csv", "xlsx", "yaml", "toml", "tsv"]);
    assert_eq!(targets("yaml"), ["json", "toml"]);
    assert_eq!(targets("toml"), ["json", "yaml"]);
}
