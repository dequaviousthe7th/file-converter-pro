"""
Data/Spreadsheet Converter Module
Handles conversions between CSV, XLSX, JSON, TSV, and HTML table formats.
"""

import os
import json
from pathlib import Path
from backend.converters.base_converter import BaseConverter, ConversionError

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class DataConverter(BaseConverter):
    """Convert between data/spreadsheet formats"""

    SUPPORTED_OUTPUTS = ['csv', 'xlsx', 'json', 'tsv', 'html']

    def convert(self, input_path: str, output_path: str, target_format: str) -> bool:
        if not PANDAS_AVAILABLE:
            raise ConversionError("pandas not installed", "pip install pandas openpyxl")

        self.check_cancel()
        ext = Path(input_path).suffix.lower().lstrip('.')

        try:
            self.report_progress(10, "Loading data...")
            df = self._read_file(input_path, ext)
            self.check_cancel()
            self.report_progress(50, f"Converting to {target_format.upper()}...")
            self._write_file(df, output_path, target_format)
            self.report_progress(100, "Done")
            return True
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"Data conversion failed: {e}")

    def _read_file(self, path: str, ext: str) -> 'pd.DataFrame':
        """Read input file into a pandas DataFrame."""
        if ext == 'csv':
            return pd.read_csv(path, encoding='utf-8', encoding_errors='replace')
        elif ext == 'xlsx':
            if not OPENPYXL_AVAILABLE:
                raise ConversionError("openpyxl needed for Excel", "pip install openpyxl")
            return pd.read_excel(path, engine='openpyxl')
        elif ext == 'json':
            return self._read_json(path)
        elif ext == 'tsv':
            return pd.read_csv(path, sep='\t', encoding='utf-8', encoding_errors='replace')
        else:
            raise ConversionError(f"Cannot read .{ext} files")

    def _read_json(self, path: str) -> 'pd.DataFrame':
        """Read JSON into DataFrame, handling both array and object formats."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            # Try to find tabular data in the dict
            for key, val in data.items():
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    return pd.DataFrame(val)
            # Fallback: treat dict as single row or use json_normalize
            return pd.json_normalize(data)
        else:
            raise ConversionError("JSON structure not supported for tabular conversion")

    def _write_file(self, df: 'pd.DataFrame', path: str, fmt: str):
        """Write DataFrame to target format."""
        if fmt == 'csv':
            df.to_csv(path, index=False, encoding='utf-8')
        elif fmt == 'xlsx':
            if not OPENPYXL_AVAILABLE:
                raise ConversionError("openpyxl needed for Excel", "pip install openpyxl")
            df.to_excel(path, index=False, engine='openpyxl')
        elif fmt == 'json':
            df.to_json(path, orient='records', indent=2, force_ascii=False)
        elif fmt == 'tsv':
            df.to_csv(path, sep='\t', index=False, encoding='utf-8')
        elif fmt == 'html':
            html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Data Table</title>
<style>
body{{font-family:Arial,sans-serif;margin:40px;}}
table{{border-collapse:collapse;width:100%;}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left;}}
th{{background:#4a90d9;color:white;}}
tr:nth-child(even){{background:#f2f2f2;}}
</style></head><body>
{df.to_html(index=False, classes='data-table')}
</body></html>"""
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
        else:
            raise ConversionError(f"Unsupported output format: {fmt}")
