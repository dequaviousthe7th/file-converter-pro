"""
Base Converter Module
All converters inherit from this. Provides cancel support and progress callbacks.
"""

import threading
from typing import Optional, Callable


class ConversionError(Exception):
    """Custom exception for conversion errors with user-friendly messages."""
    def __init__(self, message, detail=None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class BaseConverter:
    """Base class for all file converters."""

    SUPPORTED_OUTPUTS = []

    def __init__(self, cancel_event: Optional[threading.Event] = None,
                 progress_callback: Optional[Callable[[int, str], None]] = None):
        self._cancel_event = cancel_event or threading.Event()
        self._progress_callback = progress_callback

    def is_cancelled(self):
        """Check if conversion has been cancelled."""
        return self._cancel_event.is_set()

    def check_cancel(self):
        """Check cancel and raise if cancelled. Call this at key points in conversion."""
        if self._cancel_event.is_set():
            raise ConversionError("Conversion cancelled by user")

    def report_progress(self, percent: int, message: str = ""):
        """Report progress to the UI."""
        if self._progress_callback:
            try:
                self._progress_callback(min(percent, 100), message)
            except Exception:
                pass

    def convert(self, input_path: str, output_path: str, target_format: str) -> bool:
        """Override in subclass."""
        raise NotImplementedError
