"""
Word Converter Module
Handles conversions from DOCX to other formats
"""

import os
import re
from pathlib import Path
from backend.converters.base_converter import BaseConverter, ConversionError

try:
    from docx import Document
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False

try:
    import docx2pdf
    DOCX2PDF_AVAILABLE = True
except ImportError:
    DOCX2PDF_AVAILABLE = False


class WordConverter(BaseConverter):
    """Convert Word (DOCX) files to various formats"""

    SUPPORTED_OUTPUTS = ['pdf', 'txt', 'md', 'html']

    def convert(self, input_path: str, output_path: str, target_format: str) -> bool:
        self.check_cancel()
        if target_format == 'pdf':
            return self._to_pdf(input_path, output_path)
        elif target_format in ['txt', 'md']:
            return self._to_text(input_path, output_path, target_format)
        elif target_format == 'html':
            return self._to_html(input_path, output_path)
        else:
            raise ConversionError(f"Unsupported target format: {target_format}")

    def _to_pdf(self, input_path: str, output_path: str) -> bool:
        self.report_progress(10, "Converting Word to PDF...")
        if DOCX2PDF_AVAILABLE:
            try:
                docx2pdf.convert(input_path, output_path)
                self.report_progress(100, "Done")
                return True
            except Exception:
                pass

        # Fallback: LibreOffice
        self.report_progress(30, "Trying LibreOffice fallback...")
        return self._convert_with_libreoffice(input_path, output_path)

    def _convert_with_libreoffice(self, input_path: str, output_path: str) -> bool:
        try:
            import subprocess
            output_dir = os.path.dirname(output_path)
            cmd = [
                'libreoffice', '--headless', '--convert-to', 'pdf',
                '--outdir', output_dir, input_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                base_name = Path(input_path).stem
                expected_output = os.path.join(output_dir, f"{base_name}.pdf")
                if os.path.exists(expected_output) and expected_output != output_path:
                    os.rename(expected_output, output_path)
                self.report_progress(100, "Done")
                return True
            raise ConversionError("LibreOffice conversion failed")
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"DOCX to PDF failed: {e}",
                                  "Install docx2pdf or LibreOffice")

    def _extract_doc_content(self, input_path):
        """Extract paragraphs and tables from DOCX."""
        if not PYTHON_DOCX_AVAILABLE:
            raise ConversionError("python-docx not installed", "pip install python-docx")
        return Document(input_path)

    def _to_text(self, input_path: str, output_path: str, format_type: str) -> bool:
        try:
            self.report_progress(10, "Reading Word document...")
            doc = self._extract_doc_content(input_path)
            content_parts = []

            total = len(doc.paragraphs) + len(doc.tables)
            done = 0

            for para in doc.paragraphs:
                self.check_cancel()
                text = para.text.strip()
                if not text:
                    continue

                if format_type == 'md':
                    style_name = para.style.name.lower() if para.style else ""
                    if 'heading 1' in style_name:
                        content_parts.append(f"# {text}")
                    elif 'heading 2' in style_name:
                        content_parts.append(f"## {text}")
                    elif 'heading 3' in style_name:
                        content_parts.append(f"### {text}")
                    elif 'heading' in style_name:
                        level = re.search(r'\d+', style_name)
                        hashes = '#' * min(int(level.group()), 6) if level else '##'
                        content_parts.append(f"{hashes} {text}")
                    else:
                        formatted = ""
                        for run in para.runs:
                            rt = run.text
                            if run.bold and run.italic:
                                rt = f"***{rt}***"
                            elif run.bold:
                                rt = f"**{rt}**"
                            elif run.italic:
                                rt = f"*{rt}*"
                            formatted += rt
                        content_parts.append(formatted if formatted else text)
                else:
                    content_parts.append(text)

                done += 1
                self.report_progress(10 + int(80 * done / max(total, 1)))

            for table in doc.tables:
                self.check_cancel()
                if format_type == 'md':
                    content_parts.append("")
                    for i, row in enumerate(table.rows):
                        row_text = "| " + " | ".join(
                            cell.text.strip().replace('\n', ' ') for cell in row.cells
                        ) + " |"
                        content_parts.append(row_text)
                        if i == 0:
                            sep = "|" + "|".join(" --- " for _ in row.cells) + "|"
                            content_parts.append(sep)
                    content_parts.append("")
                else:
                    for row in table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells)
                        content_parts.append(row_text)
                    content_parts.append("-" * 50)
                done += 1

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n\n".join(content_parts))
            self.report_progress(100, "Done")
            return True
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"DOCX to text failed: {e}")

    def _to_html(self, input_path: str, output_path: str) -> bool:
        try:
            self.report_progress(10, "Reading Word document...")
            doc = self._extract_doc_content(input_path)
            html_parts = []

            for para in doc.paragraphs:
                self.check_cancel()
                text = para.text.strip()
                if not text:
                    continue
                escaped = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                style_name = para.style.name.lower() if para.style else ""
                if 'heading 1' in style_name:
                    html_parts.append(f"<h1>{escaped}</h1>")
                elif 'heading 2' in style_name:
                    html_parts.append(f"<h2>{escaped}</h2>")
                elif 'heading 3' in style_name:
                    html_parts.append(f"<h3>{escaped}</h3>")
                else:
                    html_parts.append(f"<p>{escaped}</p>")

            self.report_progress(70, "Building HTML...")
            for table in doc.tables:
                self.check_cancel()
                html_parts.append("<table border='1' cellpadding='5'>")
                for i, row in enumerate(table.rows):
                    tag = "th" if i == 0 else "td"
                    cells = "".join(f"<{tag}>{c.text.strip()}</{tag}>" for c in row.cells)
                    html_parts.append(f"<tr>{cells}</tr>")
                html_parts.append("</table>")

            html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Converted from Word</title>
<style>body{{font-family:Arial,sans-serif;max-width:800px;margin:40px auto;line-height:1.6;}}
table{{border-collapse:collapse;width:100%;margin:1em 0;}}</style>
</head><body>
{"".join(html_parts)}
</body></html>"""

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            self.report_progress(100, "Done")
            return True
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"DOCX to HTML failed: {e}")
