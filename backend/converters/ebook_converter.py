"""
Ebook Converter Module
Handles EPUB and RTF conversions.
"""

import re
from pathlib import Path
from backend.converters.base_converter import BaseConverter, ConversionError

try:
    import ebooklib
    from ebooklib import epub
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from striprtf.striprtf import rtf_to_text
    STRIPRTF_AVAILABLE = True
except ImportError:
    STRIPRTF_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from docx import Document
    from docx.shared import Pt
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False


class EbookConverter(BaseConverter):
    """Convert ebook/RTF formats"""

    SUPPORTED_OUTPUTS = ['pdf', 'txt', 'docx']

    def convert(self, input_path: str, output_path: str, target_format: str) -> bool:
        self.check_cancel()
        ext = Path(input_path).suffix.lower().lstrip('.')

        if ext == 'epub':
            return self._convert_epub(input_path, output_path, target_format)
        elif ext == 'rtf':
            return self._convert_rtf(input_path, output_path, target_format)
        else:
            raise ConversionError(f"Unsupported input format: {ext}")

    def _extract_epub_text(self, input_path: str) -> str:
        """Extract plain text from EPUB."""
        if not EBOOKLIB_AVAILABLE:
            raise ConversionError("ebooklib not installed", "pip install ebooklib")

        self.report_progress(10, "Reading EPUB...")
        book = epub.read_epub(input_path)
        text_parts = []

        items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        total = len(items)
        for i, item in enumerate(items):
            self.check_cancel()
            content = item.get_content().decode('utf-8', errors='ignore')
            if BS4_AVAILABLE:
                soup = BeautifulSoup(content, 'html.parser')
                for tag in soup(['script', 'style']):
                    tag.decompose()
                text = soup.get_text(separator='\n', strip=True)
            else:
                text = re.sub(r'<[^>]+>', '', content)
            if text.strip():
                text_parts.append(text.strip())
            self.report_progress(10 + int(60 * (i + 1) / max(total, 1)))

        return "\n\n".join(text_parts)

    def _extract_rtf_text(self, input_path: str) -> str:
        """Extract plain text from RTF."""
        if not STRIPRTF_AVAILABLE:
            raise ConversionError("striprtf not installed", "pip install striprtf")

        self.report_progress(10, "Reading RTF...")
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            rtf_content = f.read()
        return rtf_to_text(rtf_content)

    def _convert_epub(self, input_path: str, output_path: str, target_format: str) -> bool:
        text = self._extract_epub_text(input_path)
        self.check_cancel()
        self.report_progress(70, f"Writing {target_format.upper()}...")

        if target_format == 'txt':
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
        elif target_format == 'pdf':
            self._text_to_pdf(text, output_path)
        elif target_format == 'docx':
            self._text_to_docx(text, output_path)
        else:
            raise ConversionError(f"Unsupported target: {target_format}")

        self.report_progress(100, "Done")
        return True

    def _convert_rtf(self, input_path: str, output_path: str, target_format: str) -> bool:
        text = self._extract_rtf_text(input_path)
        self.check_cancel()
        self.report_progress(50, f"Writing {target_format.upper()}...")

        if target_format == 'txt':
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
        elif target_format == 'pdf':
            self._text_to_pdf(text, output_path)
        elif target_format == 'docx':
            self._text_to_docx(text, output_path)
        else:
            raise ConversionError(f"Unsupported target: {target_format}")

        self.report_progress(100, "Done")
        return True

    def _text_to_pdf(self, text: str, output_path: str):
        if not REPORTLAB_AVAILABLE:
            raise ConversionError("reportlab not installed for PDF generation")
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        for para in text.split('\n\n'):
            if para.strip():
                safe = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(safe.replace('\n', '<br/>'), styles['Normal']))
                story.append(Spacer(1, 12))
        doc.build(story)

    def _text_to_docx(self, text: str, output_path: str):
        if not PYTHON_DOCX_AVAILABLE:
            raise ConversionError("python-docx not installed")
        doc = Document()
        for para in text.split('\n\n'):
            if para.strip():
                doc.add_paragraph(para.strip())
        doc.save(output_path)
