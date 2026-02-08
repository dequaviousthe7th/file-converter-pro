"""
PDF Converter Module
Handles conversions from PDF to other formats
"""

import os
from pathlib import Path
from typing import Optional
from backend.converters.base_converter import BaseConverter, ConversionError

try:
    from pdf2docx import Converter as PDF2DocxConverter
    PDF2DOCX_AVAILABLE = True
except ImportError:
    PDF2DOCX_AVAILABLE = False

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class PDFConverter(BaseConverter):
    """Convert PDF files to various formats"""

    SUPPORTED_OUTPUTS = ['docx', 'txt', 'md', 'png', 'jpg', 'html']

    def convert(self, input_path: str, output_path: str, target_format: str) -> bool:
        self.check_cancel()
        if target_format == 'docx':
            return self._to_docx(input_path, output_path)
        elif target_format in ['txt', 'md']:
            return self._to_text(input_path, output_path, target_format)
        elif target_format in ['png', 'jpg']:
            return self._to_image(input_path, output_path, target_format)
        elif target_format == 'html':
            return self._to_html(input_path, output_path)
        else:
            raise ConversionError(f"Unsupported target format: {target_format}")

    def _to_docx(self, input_path: str, output_path: str) -> bool:
        if not PDF2DOCX_AVAILABLE:
            raise ConversionError("pdf2docx library not installed", "pip install pdf2docx")
        try:
            self.report_progress(10, "Opening PDF...")
            cv = PDF2DocxConverter(input_path)
            self.check_cancel()
            self.report_progress(30, "Converting to Word...")
            cv.convert(output_path, start=0, end=None)
            cv.close()
            self.report_progress(100, "Done")
            return True
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"PDF to DOCX failed: {e}")

    def _to_text(self, input_path: str, output_path: str, format_type: str) -> bool:
        if not PYPDF_AVAILABLE:
            raise ConversionError("pypdf library not installed", "pip install pypdf")
        try:
            self.report_progress(10, "Reading PDF...")
            reader = PdfReader(input_path)
            total_pages = len(reader.pages)
            text_content = []

            for i, page in enumerate(reader.pages):
                self.check_cancel()
                text = page.extract_text()
                if text:
                    text_content.append(text)
                self.report_progress(10 + int(80 * (i + 1) / total_pages),
                                     f"Extracting page {i + 1} of {total_pages}...")

            full_text = "\n\n".join(text_content)

            if format_type == 'md':
                full_text = f"# Converted Document\n\n{full_text}"
                full_text = full_text.replace('\n\n\n', '\n\n')

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_text)

            self.report_progress(100, "Done")
            return True
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"PDF to text failed: {e}")

    def _to_image(self, input_path: str, output_path: str, image_format: str) -> bool:
        try:
            self.report_progress(10, "Converting PDF to image...")
            # Try pdf2image first (best quality)
            try:
                from pdf2image import convert_from_path
                self.check_cancel()
                images = convert_from_path(input_path, first_page=1, last_page=1)
                if images:
                    self.report_progress(80, "Saving image...")
                    if image_format.upper() == 'JPG':
                        images[0].convert('RGB').save(output_path, format='JPEG', quality=95)
                    else:
                        images[0].save(output_path, format=image_format.upper())
                    self.report_progress(100, "Done")
                    return True
            except ImportError:
                pass

            # Fallback: text-rendered image
            if not PYPDF_AVAILABLE or not PIL_AVAILABLE:
                raise ConversionError("Required libraries not available for PDF to image conversion")

            reader = PdfReader(input_path)
            text = reader.pages[0].extract_text()[:500] if reader.pages else "Empty PDF"

            from utils.platform_utils import find_system_font

            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)

            font_path = find_system_font()
            try:
                font = ImageFont.truetype(font_path, 20) if font_path else ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()

            y_position = 50
            draw.text((50, y_position), "PDF Preview (Text Extraction)", fill='black', font=font)
            y_position += 50

            words = text.split()
            line = ""
            for word in words:
                test_line = line + word + " "
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] <= 700:
                    line = test_line
                else:
                    draw.text((50, y_position), line, fill='black', font=font)
                    y_position += 30
                    line = word + " "
                    if y_position > 550:
                        break
            if line:
                draw.text((50, y_position), line, fill='black', font=font)

            if image_format.upper() == 'JPG':
                img.save(output_path, format='JPEG', quality=95)
            else:
                img.save(output_path, format=image_format.upper())
            self.report_progress(100, "Done")
            return True

        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"PDF to image failed: {e}")

    def _to_html(self, input_path: str, output_path: str) -> bool:
        if not PYPDF_AVAILABLE:
            raise ConversionError("pypdf library not installed")
        try:
            self.report_progress(10, "Reading PDF...")
            reader = PdfReader(input_path)
            total_pages = len(reader.pages)
            text_parts = []

            for i, page in enumerate(reader.pages):
                self.check_cancel()
                text = page.extract_text()
                if text:
                    escaped = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    text_parts.append(f"<p>{escaped.replace(chr(10), '<br>')}</p>")
                self.report_progress(10 + int(80 * (i + 1) / total_pages),
                                     f"Processing page {i + 1}...")

            html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Converted from PDF</title>
<style>body{{font-family:Arial,sans-serif;max-width:800px;margin:40px auto;line-height:1.6;}}</style>
</head><body>
{"".join(text_parts)}
</body></html>"""

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            self.report_progress(100, "Done")
            return True
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"PDF to HTML failed: {e}")
