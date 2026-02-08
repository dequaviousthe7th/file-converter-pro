"""
Settings Manager
Persistent settings saved to a JSON file.
"""

import json
from pathlib import Path


DEFAULTS = {
    "output_dir": "",  # Empty = use ./converted relative to app
    "after_conversion": "ask",  # "open_folder", "notify", "ask"
    "audio_bitrate": "192k",
    "image_quality": 85,
    "last_ui": "simple",  # "simple" or "advanced"
    "theme": "dark",  # For advanced UI
}


class Settings:
    """Manage persistent application settings."""

    def __init__(self, settings_file=None):
        if settings_file is None:
            self._file = Path.home() / ".file-converter-pro" / "settings.json"
        else:
            self._file = Path(settings_file)
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if self._file.exists():
            try:
                with open(self._file, 'r') as f:
                    saved = json.load(f)
                self._data.update(saved)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        try:
            with open(self._file, 'w') as f:
                json.dump(self._data, f, indent=2)
        except OSError:
            pass

    def get(self, key, default=None):
        return self._data.get(key, default if default is not None else DEFAULTS.get(key))

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def reset(self):
        self._data = dict(DEFAULTS)
        self.save()

    @property
    def output_dir(self):
        return self._data.get("output_dir", "")

    @property
    def after_conversion(self):
        return self._data.get("after_conversion", "ask")

    @property
    def audio_bitrate(self):
        return self._data.get("audio_bitrate", "192k")

    @property
    def image_quality(self):
        return self._data.get("image_quality", 85)
