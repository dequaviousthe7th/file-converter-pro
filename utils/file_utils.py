"""
File utility functions for File Converter Pro.
Handles temp files, file validation, and safe operations.
"""

import os
import tempfile
from pathlib import Path
from contextlib import contextmanager


@contextmanager
def safe_temp_file(suffix=".tmp", dir=None):
    """Context manager that creates a temp file and ensures cleanup."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=dir)
    try:
        tmp.close()
        yield tmp.name
    finally:
        try:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)
        except OSError:
            pass


def validate_file(path):
    """Validate that a file exists and is readable."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not p.is_file():
        raise ValueError(f"Not a file: {path}")
    if p.stat().st_size == 0:
        raise ValueError(f"File is empty: {path}")
    return True


def get_file_size_str(size_bytes):
    """Convert bytes to human-readable size string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def ensure_unique_path(path):
    """If path exists, append (1), (2), etc. to make it unique."""
    p = Path(path)
    if not p.exists():
        return str(p)
    stem = p.stem
    suffix = p.suffix
    parent = p.parent
    counter = 1
    while True:
        new_path = parent / f"{stem} ({counter}){suffix}"
        if not new_path.exists():
            return str(new_path)
        counter += 1
