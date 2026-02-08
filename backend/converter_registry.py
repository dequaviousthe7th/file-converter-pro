"""
Converter Registry
Maps file extensions to their converter classes. Single source of truth for
both UIs to determine which conversions are available.
"""

import threading
from pathlib import Path
from backend.converters.base_converter import BaseConverter, ConversionError
from backend.converters.pdf_converter import PDFConverter
from backend.converters.word_converter import WordConverter
from backend.converters.markdown_converter import MarkdownConverter
from backend.converters.image_converter import ImageConverter
from backend.converters.text_converter import TextConverter
from backend.converters.audio_converter import AudioConverter
from backend.converters.video_converter import VideoConverter
from backend.converters.data_converter import DataConverter
from backend.converters.code_converter import CodeConverter
from backend.converters.html_converter import HTMLConverter
from backend.converters.ebook_converter import EbookConverter

# Extension -> Converter class mapping
CONVERTER_MAP = {
    # Documents
    'pdf':  PDFConverter,
    'docx': WordConverter,
    'md':   MarkdownConverter,
    'txt':  TextConverter,
    'html': HTMLConverter,
    'htm':  HTMLConverter,
    'rtf':  EbookConverter,
    'epub': EbookConverter,

    # Images
    'png':  ImageConverter,
    'jpg':  ImageConverter,
    'jpeg': ImageConverter,
    'webp': ImageConverter,
    'bmp':  ImageConverter,
    'tiff': ImageConverter,
    'tif':  ImageConverter,
    'gif':  ImageConverter,
    'ico':  ImageConverter,
    'svg':  ImageConverter,
    'heic': ImageConverter,
    'heif': ImageConverter,

    # Audio
    'mp3':  AudioConverter,
    'wav':  AudioConverter,
    'flac': AudioConverter,
    'ogg':  AudioConverter,
    'aac':  AudioConverter,
    'm4a':  AudioConverter,
    'wma':  AudioConverter,

    # Video
    'mp4':  VideoConverter,
    'avi':  VideoConverter,
    'mkv':  VideoConverter,
    'mov':  VideoConverter,
    'webm': VideoConverter,

    # Data/Spreadsheets
    'csv':  DataConverter,
    'xlsx': DataConverter,
    'tsv':  DataConverter,

    # Config - JSON can be data or config, we handle via target format
    'json': DataConverter,
    'yaml': CodeConverter,
    'yml':  CodeConverter,
    'toml': CodeConverter,
}


def get_converter(ext, cancel_event=None, progress_callback=None):
    """Get the appropriate converter instance for a file extension.

    Args:
        ext: File extension (without dot)
        cancel_event: Optional threading.Event for cancellation
        progress_callback: Optional callback(percent, message)

    Returns:
        BaseConverter subclass instance
    """
    ext = ext.lower().lstrip('.')
    cls = CONVERTER_MAP.get(ext)
    if cls is None:
        raise ConversionError(f"No converter available for .{ext} files")

    # Handle JSON special case: if target is yaml/toml, use CodeConverter
    return cls(cancel_event=cancel_event, progress_callback=progress_callback)


def get_json_converter(target_format, cancel_event=None, progress_callback=None):
    """Special handler for JSON which can go to data formats OR config formats."""
    if target_format in ('yaml', 'toml'):
        return CodeConverter(cancel_event=cancel_event, progress_callback=progress_callback)
    return DataConverter(cancel_event=cancel_event, progress_callback=progress_callback)


def is_supported(ext):
    """Check if a file extension is supported."""
    return ext.lower().lstrip('.') in CONVERTER_MAP
