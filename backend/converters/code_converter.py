"""
Code/Config Converter Module
Handles conversions between JSON, YAML, TOML configuration formats.
"""

import json
from pathlib import Path
from backend.converters.base_converter import BaseConverter, ConversionError

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    import toml
    TOML_AVAILABLE = True
except ImportError:
    try:
        import tomli as toml
        TOML_AVAILABLE = True
    except ImportError:
        TOML_AVAILABLE = False

try:
    import toml as toml_write
    TOML_WRITE_AVAILABLE = True
except ImportError:
    TOML_WRITE_AVAILABLE = False


class CodeConverter(BaseConverter):
    """Convert between config/code data formats"""

    SUPPORTED_OUTPUTS = ['json', 'yaml', 'toml']

    def convert(self, input_path: str, output_path: str, target_format: str) -> bool:
        self.check_cancel()
        ext = Path(input_path).suffix.lower().lstrip('.')
        if ext == 'yml':
            ext = 'yaml'

        try:
            self.report_progress(10, "Parsing input file...")
            data = self._read(input_path, ext)
            self.check_cancel()
            self.report_progress(50, f"Writing {target_format.upper()}...")
            self._write(data, output_path, target_format)
            self.report_progress(100, "Done")
            return True
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"Config conversion failed: {e}")

    def _read(self, path: str, ext: str) -> dict:
        """Read config file into Python dict."""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if ext == 'json':
            return json.loads(content)
        elif ext == 'yaml':
            if not YAML_AVAILABLE:
                raise ConversionError("pyyaml not installed", "pip install pyyaml")
            return yaml.safe_load(content)
        elif ext == 'toml':
            if not TOML_AVAILABLE:
                raise ConversionError("toml not installed", "pip install toml")
            return toml.loads(content)
        else:
            raise ConversionError(f"Cannot read .{ext} config files")

    def _write(self, data: dict, path: str, fmt: str):
        """Write Python dict to config format."""
        with open(path, 'w', encoding='utf-8') as f:
            if fmt == 'json':
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            elif fmt == 'yaml':
                if not YAML_AVAILABLE:
                    raise ConversionError("pyyaml not installed")
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            elif fmt == 'toml':
                if not TOML_WRITE_AVAILABLE:
                    raise ConversionError("toml not installed (need writable toml)", "pip install toml")
                toml_write.dump(data, f)
            else:
                raise ConversionError(f"Unsupported output format: {fmt}")
