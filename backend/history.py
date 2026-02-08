"""
Conversion History
Stores and retrieves past conversion records.
"""

import json
import time
from pathlib import Path
from datetime import datetime


class ConversionHistory:
    """Track conversion history in a local JSON file."""

    def __init__(self, history_file=None):
        if history_file is None:
            self._file = Path.home() / ".file-converter-pro" / "history.json"
        else:
            self._file = Path(history_file)
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._records = self._load()

    def _load(self):
        if self._file.exists():
            try:
                with open(self._file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save(self):
        try:
            with open(self._file, 'w') as f:
                json.dump(self._records, f, indent=2)
        except OSError:
            pass

    def add(self, source_path, output_path, status="success", duration=0):
        """Record a conversion."""
        record = {
            "source": str(source_path),
            "output": str(output_path),
            "source_name": Path(source_path).name,
            "output_name": Path(output_path).name,
            "timestamp": time.time(),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": status,
            "duration": round(duration, 2),
        }
        self._records.insert(0, record)
        # Keep last 200 records
        self._records = self._records[:200]
        self._save()

    def get_recent(self, n=20):
        """Get the most recent n records."""
        return self._records[:n]

    def get_today(self):
        """Get records from today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return [r for r in self._records if r.get("datetime", "").startswith(today)]

    def clear(self):
        """Clear all history."""
        self._records = []
        self._save()

    @property
    def count(self):
        return len(self._records)
