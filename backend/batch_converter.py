"""
Batch Converter Engine
Queue-based batch conversion for both UIs.
"""

import threading
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable, List
from backend.converter_registry import get_converter, get_json_converter
from backend.converters.base_converter import ConversionError


@dataclass
class BatchItem:
    """Single item in the batch queue."""
    input_path: str
    target_format: str
    output_path: str = ""
    status: str = "pending"  # pending, converting, done, failed, cancelled
    progress: int = 0
    message: str = ""
    error: str = ""

    @property
    def filename(self):
        return Path(self.input_path).name

    @property
    def ext(self):
        return Path(self.input_path).suffix.lower().lstrip('.')


class BatchConverter:
    """Manages batch conversion of multiple files."""

    def __init__(self, output_dir: str,
                 on_item_update: Optional[Callable[[int, BatchItem], None]] = None,
                 on_batch_complete: Optional[Callable[[], None]] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.items: List[BatchItem] = []
        self._cancel_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._on_item_update = on_item_update
        self._on_batch_complete = on_batch_complete

    def add(self, input_path: str, target_format: str) -> int:
        """Add a file to the batch queue. Returns the item index."""
        stem = Path(input_path).stem
        output_path = str(self.output_dir / f"{stem}_converted.{target_format}")
        item = BatchItem(input_path=input_path, target_format=target_format,
                         output_path=output_path)
        self.items.append(item)
        return len(self.items) - 1

    def remove(self, index: int):
        """Remove an item from the queue (only if pending)."""
        if 0 <= index < len(self.items) and self.items[index].status == "pending":
            self.items.pop(index)

    def clear(self):
        """Clear all pending items."""
        self.items = [item for item in self.items if item.status == "converting"]

    def start(self):
        """Start converting all pending items."""
        self._cancel_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def kill(self):
        """Cancel the entire batch."""
        self._cancel_event.set()
        for item in self.items:
            if item.status in ("pending", "converting"):
                item.status = "cancelled"
                item.message = "Cancelled"
                self._notify_update(self.items.index(item), item)

    @property
    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    @property
    def total(self):
        return len(self.items)

    @property
    def completed(self):
        return sum(1 for item in self.items if item.status in ("done", "failed", "cancelled"))

    @property
    def overall_progress(self):
        if not self.items:
            return 0
        return int(100 * self.completed / len(self.items))

    def _run(self):
        """Process the queue sequentially."""
        for i, item in enumerate(self.items):
            if self._cancel_event.is_set():
                break
            if item.status != "pending":
                continue

            item.status = "converting"
            item.progress = 0
            item.message = "Starting..."
            self._notify_update(i, item)

            try:
                def progress_cb(pct, msg=""):
                    item.progress = pct
                    item.message = msg
                    self._notify_update(i, item)

                ext = item.ext
                if ext == 'json' and item.target_format in ('yaml', 'toml'):
                    converter = get_json_converter(
                        item.target_format,
                        cancel_event=self._cancel_event,
                        progress_callback=progress_cb
                    )
                else:
                    converter = get_converter(
                        ext,
                        cancel_event=self._cancel_event,
                        progress_callback=progress_cb
                    )

                converter.convert(item.input_path, item.output_path, item.target_format)
                item.status = "done"
                item.progress = 100
                item.message = "Complete"

            except ConversionError as e:
                if self._cancel_event.is_set():
                    item.status = "cancelled"
                    item.message = "Cancelled"
                else:
                    item.status = "failed"
                    item.error = str(e)
                    item.message = f"Failed: {e.message}"

            except Exception as e:
                item.status = "failed"
                item.error = str(e)
                item.message = f"Failed: {e}"

            self._notify_update(i, item)

        if self._on_batch_complete:
            try:
                self._on_batch_complete()
            except Exception:
                pass

    def _notify_update(self, index, item):
        if self._on_item_update:
            try:
                self._on_item_update(index, item)
            except Exception:
                pass
