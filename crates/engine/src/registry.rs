//! Format registry — the single source of truth for the conversion matrix.
//!
//! Reproduces the plan's "Format matrix" section verbatim (v2 `config.py` +
//! design deltas). The registry stores canonical extensions only; aliases
//! (`jpeg`, `tif`, `yml`, `heif`, `htm`) are normalized on input.

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
pub enum Category {
    Documents,
    Images,
    Audio,
    Video,
    Data,
    Config,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct FormatInfo {
    pub ext: &'static str,
    pub name: &'static str,
    pub category: Category,
    pub targets: &'static [&'static str],
    pub icon: &'static str,
}

const fn fmt(
    ext: &'static str,
    name: &'static str,
    category: Category,
    targets: &'static [&'static str],
    icon: &'static str,
) -> FormatInfo {
    FormatInfo {
        ext,
        name,
        category,
        targets,
        icon,
    }
}

static FORMATS: &[FormatInfo] = &[
    // Documents
    fmt(
        "pdf",
        "PDF",
        Category::Documents,
        &["docx", "txt", "md", "png", "jpg", "html"],
        "📄",
    ),
    fmt(
        "docx",
        "Word",
        Category::Documents,
        &["pdf", "txt", "md", "html"],
        "📝",
    ),
    fmt(
        "md",
        "Markdown",
        Category::Documents,
        &["pdf", "docx", "txt", "html"],
        "📑",
    ),
    fmt(
        "txt",
        "Text",
        Category::Documents,
        &["pdf", "docx", "md"],
        "📃",
    ),
    fmt(
        "html",
        "HTML",
        Category::Documents,
        &["pdf", "docx", "txt", "md"],
        "🌐",
    ),
    fmt(
        "rtf",
        "RTF",
        Category::Documents,
        &["pdf", "docx", "txt"],
        "📄",
    ),
    fmt(
        "epub",
        "EPUB",
        Category::Documents,
        &["pdf", "txt", "docx"],
        "📚",
    ),
    // Images
    fmt(
        "png",
        "PNG",
        Category::Images,
        &["jpg", "webp", "bmp", "pdf", "tiff", "ico", "gif"],
        "🖼️",
    ),
    fmt(
        "jpg",
        "JPG",
        Category::Images,
        &["png", "webp", "bmp", "pdf", "tiff", "ico", "gif"],
        "🖼️",
    ),
    fmt(
        "webp",
        "WebP",
        Category::Images,
        &["png", "jpg", "bmp", "pdf", "tiff", "gif"],
        "🖼️",
    ),
    fmt(
        "bmp",
        "BMP",
        Category::Images,
        &["png", "jpg", "webp", "pdf", "tiff", "gif"],
        "🖼️",
    ),
    fmt(
        "tiff",
        "TIFF",
        Category::Images,
        &["png", "jpg", "webp", "bmp", "pdf", "gif"],
        "🖼️",
    ),
    fmt(
        "gif",
        "GIF",
        Category::Images,
        &["png", "jpg", "webp", "bmp", "pdf"],
        "🖼️",
    ),
    fmt("ico", "ICO", Category::Images, &["png", "jpg", "bmp"], "🖼️"),
    fmt(
        "svg",
        "SVG",
        Category::Images,
        &["png", "jpg", "webp", "pdf"],
        "🖼️",
    ),
    fmt(
        "heic",
        "HEIC",
        Category::Images,
        &["png", "jpg", "webp", "bmp", "pdf", "tiff"],
        "🖼️",
    ),
    // Audio
    fmt(
        "mp3",
        "MP3",
        Category::Audio,
        &["wav", "flac", "ogg", "aac", "m4a", "wma"],
        "🎵",
    ),
    fmt(
        "wav",
        "WAV",
        Category::Audio,
        &["mp3", "flac", "ogg", "aac", "m4a"],
        "🎵",
    ),
    fmt(
        "flac",
        "FLAC",
        Category::Audio,
        &["mp3", "wav", "ogg", "aac", "m4a"],
        "🎵",
    ),
    fmt(
        "ogg",
        "OGG",
        Category::Audio,
        &["mp3", "wav", "flac", "aac", "m4a"],
        "🎵",
    ),
    fmt(
        "aac",
        "AAC",
        Category::Audio,
        &["mp3", "wav", "flac", "ogg", "m4a"],
        "🎵",
    ),
    fmt(
        "m4a",
        "M4A",
        Category::Audio,
        &["mp3", "wav", "flac", "ogg", "aac"],
        "🎵",
    ),
    fmt(
        "wma",
        "WMA",
        Category::Audio,
        &["mp3", "wav", "flac", "ogg", "m4a"],
        "🎵",
    ),
    // Video
    fmt(
        "mp4",
        "MP4",
        Category::Video,
        &["avi", "mkv", "mov", "webm", "gif"],
        "🎬",
    ),
    fmt(
        "avi",
        "AVI",
        Category::Video,
        &["mp4", "mkv", "mov", "webm", "gif"],
        "🎬",
    ),
    fmt(
        "mkv",
        "MKV",
        Category::Video,
        &["mp4", "avi", "mov", "webm", "gif"],
        "🎬",
    ),
    fmt(
        "mov",
        "MOV",
        Category::Video,
        &["mp4", "avi", "mkv", "webm", "gif"],
        "🎬",
    ),
    fmt(
        "webm",
        "WebM",
        Category::Video,
        &["mp4", "avi", "mkv", "mov", "gif"],
        "🎬",
    ),
    // Data
    fmt(
        "csv",
        "CSV",
        Category::Data,
        &["xlsx", "json", "tsv", "html"],
        "📊",
    ),
    fmt(
        "xlsx",
        "Excel",
        Category::Data,
        &["csv", "json", "tsv", "html"],
        "📊",
    ),
    fmt(
        "json",
        "JSON",
        Category::Data,
        &["csv", "xlsx", "yaml", "toml", "tsv"],
        "📊",
    ),
    fmt("tsv", "TSV", Category::Data, &["csv", "xlsx", "json"], "📊"),
    // Config
    fmt("yaml", "YAML", Category::Config, &["json", "toml"], "⚙️"),
    fmt("toml", "TOML", Category::Config, &["json", "yaml"], "⚙️"),
];

pub fn formats() -> &'static [FormatInfo] {
    FORMATS
}

/// Normalize an extension: strips a leading dot, maps aliases
/// (`jpeg`→`jpg`, `tif`→`tiff`, `yml`→`yaml`, `heif`→`heic`, `htm`→`html`)
/// and returns the canonical lowercase form for any known format,
/// case-insensitively. Unknown extensions are returned unchanged.
pub fn normalize_ext(ext: &str) -> &str {
    let ext = ext.strip_prefix('.').unwrap_or(ext);
    match () {
        _ if ext.eq_ignore_ascii_case("jpeg") => "jpg",
        _ if ext.eq_ignore_ascii_case("tif") => "tiff",
        _ if ext.eq_ignore_ascii_case("yml") => "yaml",
        _ if ext.eq_ignore_ascii_case("heif") => "heic",
        _ if ext.eq_ignore_ascii_case("htm") => "html",
        _ => match FORMATS.iter().find(|f| f.ext.eq_ignore_ascii_case(ext)) {
            Some(f) => f.ext,
            None => ext,
        },
    }
}

/// Look up a format by extension (case-insensitive, aliases accepted).
pub fn format_for(ext: &str) -> Option<&'static FormatInfo> {
    let ext = normalize_ext(ext);
    FORMATS.iter().find(|f| f.ext == ext)
}

/// Whether the extension (case-insensitive, aliases accepted) is a supported source format.
pub fn is_supported(ext: &str) -> bool {
    format_for(ext).is_some()
}

/// Total number of conversion pairs in the matrix.
pub fn total_pairs() -> usize {
    FORMATS.iter().map(|f| f.targets.len()).sum()
}
