"""
File Converter Pro - Centralized Configuration
Single source of truth for version, app info, and format registry.
"""

VERSION = "2.0.0"
APP_NAME = "File Converter Pro"
AUTHOR = "Dequavious"
OUTPUT_DIR_NAME = "converted"

# Complete format registry - single source of truth
# Both UIs read from this. Categories help organize the UI.
FORMATS = {
    # Documents
    'pdf':   {'name': 'PDF',      'icon': '📄', 'category': 'Documents', 'to': ['docx', 'txt', 'md', 'png', 'jpg', 'html']},
    'docx':  {'name': 'Word',     'icon': '📝', 'category': 'Documents', 'to': ['pdf', 'txt', 'md', 'html']},
    'md':    {'name': 'Markdown', 'icon': '📑', 'category': 'Documents', 'to': ['pdf', 'docx', 'txt', 'html']},
    'txt':   {'name': 'Text',     'icon': '📃', 'category': 'Documents', 'to': ['pdf', 'docx', 'md']},
    'html':  {'name': 'HTML',     'icon': '🌐', 'category': 'Documents', 'to': ['pdf', 'docx', 'txt', 'md']},
    'rtf':   {'name': 'RTF',      'icon': '📄', 'category': 'Documents', 'to': ['pdf', 'docx', 'txt']},
    'epub':  {'name': 'EPUB',     'icon': '📚', 'category': 'Documents', 'to': ['pdf', 'txt']},

    # Images
    'png':   {'name': 'PNG',  'icon': '🖼️', 'category': 'Images', 'to': ['jpg', 'webp', 'bmp', 'pdf', 'tiff', 'ico', 'gif']},
    'jpg':   {'name': 'JPG',  'icon': '🖼️', 'category': 'Images', 'to': ['png', 'webp', 'bmp', 'pdf', 'tiff', 'ico', 'gif']},
    'jpeg':  {'name': 'JPEG', 'icon': '🖼️', 'category': 'Images', 'to': ['png', 'webp', 'bmp', 'pdf', 'tiff', 'ico', 'gif']},
    'webp':  {'name': 'WebP', 'icon': '🖼️', 'category': 'Images', 'to': ['png', 'jpg', 'bmp', 'pdf', 'tiff', 'gif']},
    'bmp':   {'name': 'BMP',  'icon': '🖼️', 'category': 'Images', 'to': ['png', 'jpg', 'webp', 'pdf', 'tiff', 'gif']},
    'tiff':  {'name': 'TIFF', 'icon': '🖼️', 'category': 'Images', 'to': ['png', 'jpg', 'webp', 'bmp', 'pdf', 'gif']},
    'tif':   {'name': 'TIFF', 'icon': '🖼️', 'category': 'Images', 'to': ['png', 'jpg', 'webp', 'bmp', 'pdf', 'gif']},
    'gif':   {'name': 'GIF',  'icon': '🖼️', 'category': 'Images', 'to': ['png', 'jpg', 'webp', 'bmp', 'pdf']},
    'ico':   {'name': 'ICO',  'icon': '🖼️', 'category': 'Images', 'to': ['png', 'jpg', 'bmp']},
    'svg':   {'name': 'SVG',  'icon': '🖼️', 'category': 'Images', 'to': ['png', 'jpg', 'webp', 'pdf']},
    'heic':  {'name': 'HEIC', 'icon': '🖼️', 'category': 'Images', 'to': ['png', 'jpg', 'webp', 'bmp', 'pdf', 'tiff']},
    'heif':  {'name': 'HEIF', 'icon': '🖼️', 'category': 'Images', 'to': ['png', 'jpg', 'webp', 'bmp', 'pdf', 'tiff']},

    # Audio
    'mp3':   {'name': 'MP3',  'icon': '🎵', 'category': 'Audio', 'to': ['wav', 'flac', 'ogg', 'aac', 'm4a', 'wma']},
    'wav':   {'name': 'WAV',  'icon': '🎵', 'category': 'Audio', 'to': ['mp3', 'flac', 'ogg', 'aac', 'm4a']},
    'flac':  {'name': 'FLAC', 'icon': '🎵', 'category': 'Audio', 'to': ['mp3', 'wav', 'ogg', 'aac', 'm4a']},
    'ogg':   {'name': 'OGG',  'icon': '🎵', 'category': 'Audio', 'to': ['mp3', 'wav', 'flac', 'aac', 'm4a']},
    'aac':   {'name': 'AAC',  'icon': '🎵', 'category': 'Audio', 'to': ['mp3', 'wav', 'flac', 'ogg', 'm4a']},
    'm4a':   {'name': 'M4A',  'icon': '🎵', 'category': 'Audio', 'to': ['mp3', 'wav', 'flac', 'ogg', 'aac']},
    'wma':   {'name': 'WMA',  'icon': '🎵', 'category': 'Audio', 'to': ['mp3', 'wav', 'flac', 'ogg', 'm4a']},

    # Video
    'mp4':   {'name': 'MP4',  'icon': '🎬', 'category': 'Video', 'to': ['avi', 'mkv', 'mov', 'webm', 'gif']},
    'avi':   {'name': 'AVI',  'icon': '🎬', 'category': 'Video', 'to': ['mp4', 'mkv', 'mov', 'webm', 'gif']},
    'mkv':   {'name': 'MKV',  'icon': '🎬', 'category': 'Video', 'to': ['mp4', 'avi', 'mov', 'webm', 'gif']},
    'mov':   {'name': 'MOV',  'icon': '🎬', 'category': 'Video', 'to': ['mp4', 'avi', 'mkv', 'webm', 'gif']},
    'webm':  {'name': 'WebM', 'icon': '🎬', 'category': 'Video', 'to': ['mp4', 'avi', 'mkv', 'mov', 'gif']},

    # Data/Spreadsheets
    'csv':   {'name': 'CSV',      'icon': '📊', 'category': 'Data', 'to': ['xlsx', 'json', 'tsv', 'html']},
    'xlsx':  {'name': 'Excel',    'icon': '📊', 'category': 'Data', 'to': ['csv', 'json', 'tsv', 'html']},
    'json':  {'name': 'JSON',     'icon': '📊', 'category': 'Data', 'to': ['csv', 'xlsx', 'yaml', 'toml', 'tsv']},
    'tsv':   {'name': 'TSV',      'icon': '📊', 'category': 'Data', 'to': ['csv', 'xlsx', 'json']},

    # Config/Code
    'yaml':  {'name': 'YAML', 'icon': '⚙️', 'category': 'Config', 'to': ['json', 'toml']},
    'yml':   {'name': 'YAML', 'icon': '⚙️', 'category': 'Config', 'to': ['json', 'toml']},
    'toml':  {'name': 'TOML', 'icon': '⚙️', 'category': 'Config', 'to': ['json', 'yaml']},
}

# Build filetypes for browse dialogs
def get_filetypes():
    """Return filetypes list for file dialogs."""
    all_exts = " ".join(f"*.{ext}" for ext in FORMATS)
    types = [("All Supported", all_exts)]

    categories = {}
    for ext, info in FORMATS.items():
        cat = info['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f"*.{ext}")

    for cat, exts in categories.items():
        types.append((cat, " ".join(exts)))

    types.append(("All Files", "*.*"))
    return types


def get_formats_by_category():
    """Group formats by category for UI display."""
    cats = {}
    seen = set()
    for ext, info in FORMATS.items():
        cat = info['category']
        if cat not in cats:
            cats[cat] = []
        # Avoid duplicate entries (e.g., jpg/jpeg, tiff/tif, yaml/yml)
        if info['name'] not in seen or ext in ('jpg', 'tiff', 'yaml'):
            cats[cat].append(ext)
            seen.add(info['name'])
    return cats
